"""第 41 课可离线运行的 LangChain Hybrid RAG、Query Rewrite 与索引缓存。"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from api.schemas import Citation, Intent
from config.settings import api_key_is_missing, embedding_model_name, load_course_env, openai_base_url
from course_runtime.course_logging import log_course_event
from rag.documents import load_knowledge_citation


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
KNOWLEDGE_FILES = (
    "after_sale_policy.md",
    "payment_invoice_policy.md",
    "invoice_title_faq.md",
    "promotion_policy.md",
    "member_coupon_policy.md",
    "received_return_policy.md",
)
RAG_RETRIEVAL_CACHE: dict[str, "HybridRetrievalResult"] = {}
_KNOWLEDGE_INDEX: "KnowledgeIndex | None" = None


@dataclass
class KnowledgeIndex:
    version: str
    vector_store: InMemoryVectorStore
    documents: list[Document]
    embedding_mode: str


@dataclass
class HybridRetrievalResult:
    citations: list[Citation]
    debug: dict[str, Any]


class LocalTokenEmbeddings(Embeddings):
    """确定性字符/双字向量，只用于课程离线演示，不冒充商用语义 embedding。"""

    dimensions = 256

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        normalized = normalize_query(text)
        tokens = [*normalized, *[normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))]]
        vector = [0.0] * self.dimensions
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:2], "big") % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def build_course_embeddings() -> tuple[Embeddings, str]:
    """在线默认使用真实语义 Embedding；离线替身必须由课程测试显式开启。"""
    load_course_env()
    if os.getenv("AGENT_COURSE_OFFLINE_RAG") == "1":
        return LocalTokenEmbeddings(), "local_token_embedding_for_explicit_offline_course"

    api_key = os.getenv("AGENT_OPENAI_API_KEY")
    if api_key_is_missing(api_key):
        raise RuntimeError(
            "RAG 需要 AGENT_OPENAI_API_KEY；仅离线测试可显式设置 AGENT_COURSE_OFFLINE_RAG=1"
        )
    from langchain_openai import OpenAIEmbeddings

    model_name = embedding_model_name()
    return (
        OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            base_url=openai_base_url(),
            request_timeout=30,
            max_retries=0,
            check_embedding_ctx_length=False,
        ),
        f"openai_compatible_embedding:{model_name}",
    )


def normalize_query(text: str) -> str:
    """把常见口语别名改写成知识文件里的稳定业务词。"""
    return (
        re.sub(r"\s+", "", text.lower())
        .replace("叠券", "叠加会员券")
        .replace("优惠卷", "优惠券")
        .replace("开票", "电子发票")
        .replace("退钱", "退款")
        .replace("那个", "")
        .replace("这个", "")
    )


def build_retrieval_plan(query: str, intent: Intent, knowledge_domains: list[str] | None = None) -> dict[str, Any]:
    rewritten = normalize_query(query)
    domains = {
        "promotion_query": ["promotion_and_member_policy"],
        "faq_query": ["faq"],
        "refund_request": ["after_sale_policy"],
    }.get(intent, [])
    from rag.domains import public_domains
    if knowledge_domains is not None:
        domains = public_domains(knowledge_domains)
        if knowledge_domains and not domains:
            raise ValueError("No allowed public knowledge domains")
    plan = {
        "original_query": query,
        "rewritten_query": rewritten,
        "intent": intent,
        "knowledge_domains": domains,
        "reason": "口语归一后按 RoutePlan 知识域执行向量与关键词双路召回。",
    }
    log_course_event(
        "RAG_RETRIEVAL_PLAN",
        "RAG 检索计划已生成：先改写查询，再限定知识域",
        teaching=True,
        **plan,
    )
    return plan


def get_knowledge_index() -> tuple[KnowledgeIndex, bool]:
    """按真实 Markdown 内容构建一次切块和向量索引，后续请求复用。"""
    global _KNOWLEDGE_INDEX
    if _KNOWLEDGE_INDEX is not None:
        log_course_event(
            "RAG_INDEX_REUSED",
            "知识索引已复用，不再重复切块和生成 Embedding",
            teaching=True,
            index_version=_KNOWLEDGE_INDEX.version,
            chunk_count=len(_KNOWLEDGE_INDEX.documents),
            embedding_mode=_KNOWLEDGE_INDEX.embedding_mode,
        )
        return _KNOWLEDGE_INDEX, True

    source_documents: list[Document] = []
    fingerprint_parts: list[str] = []
    for filename in KNOWLEDGE_FILES:
        path = KNOWLEDGE_DIR / filename
        text = path.read_text(encoding="utf-8")
        citation = load_knowledge_citation(filename)
        fingerprint_parts.append(f"{filename}:{text}")
        source_documents.append(
            Document(
                page_content=text.split("---", 2)[-1].strip(),
                metadata={
                    "filename": filename,
                    "source": citation.source,
                    "title": citation.title,
                    "policy_id": (citation.metadata or {}).get("policy_id"),
                    "scene_key": (citation.metadata or {}).get("scene_key"),
                    "knowledge_domain": (citation.metadata or {}).get("knowledge_domain"),
                    "base_score": citation.score,
                },
            )
        )
    splitter = RecursiveCharacterTextSplitter(chunk_size=220, chunk_overlap=30)
    chunks = splitter.split_documents(source_documents)
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{chunk.metadata['policy_id']}-chunk-{index + 1}"
    embeddings, embedding_mode = build_course_embeddings()
    vector_store = InMemoryVectorStore(embeddings)
    vector_store.add_documents(chunks)
    fingerprint_parts.append(f"embedding:{embedding_mode}")
    fingerprint = hashlib.sha256("\n".join(fingerprint_parts).encode("utf-8")).hexdigest()[:12]
    _KNOWLEDGE_INDEX = KnowledgeIndex(
        version=f"lesson41-idx-{fingerprint}",
        vector_store=vector_store,
        documents=chunks,
        embedding_mode=embedding_mode,
    )
    log_course_event(
        "RAG_INDEX_BUILT",
        "知识文件已切块并建立向量索引",
        teaching=True,
        index_version=_KNOWLEDGE_INDEX.version,
        source_count=len(source_documents),
        chunk_count=len(chunks),
        chunk_size=220,
        chunk_overlap=30,
        embedding_mode=embedding_mode,
    )
    return _KNOWLEDGE_INDEX, False


def retrieve_knowledge(query: str, intent: Intent, *, top_k: int = 4, knowledge_domains: list[str] | None = None) -> HybridRetrievalResult:
    """执行 Query Rewrite、向量召回、关键词召回、合并重排和检索缓存。"""
    plan = build_retrieval_plan(query, intent, knowledge_domains)
    index, index_cache_hit = get_knowledge_index()
    cache_key = hashlib.sha256(f"{index.version}|{intent}|{plan['knowledge_domains']}|{top_k}|{plan['rewritten_query']}".encode("utf-8")).hexdigest()[:16]
    if cache_key in RAG_RETRIEVAL_CACHE:
        cached = RAG_RETRIEVAL_CACHE[cache_key]
        log_course_event(
            "RAG_RETRIEVAL_CACHE_HIT",
            "相同索引、意图和改写查询命中检索缓存",
            teaching=True,
            cache_key=cache_key,
            index_version=index.version,
            hit_count=len(cached.citations),
        )
        return HybridRetrievalResult(
            citations=list(cached.citations),
            debug={**cached.debug, "retrieval_cache_hit": True, "index_cache_hit": True},
        )
    log_course_event(
        "RAG_RETRIEVAL_CACHE_MISS",
        "检索缓存未命中，开始执行双路召回",
        teaching=True,
        cache_key=cache_key,
        index_version=index.version,
        rewritten_query=plan["rewritten_query"],
    )

    domains = set(plan["knowledge_domains"])
    # InMemoryVectorStore 返回的就是余弦相似度；当前 LangChain 版本没有额外的
    # relevance-score 转换器，因此直接使用它支持的 score 接口。
    vector_pairs = index.vector_store.similarity_search_with_score(plan["rewritten_query"], k=top_k, filter=lambda doc: _domain_allowed(doc.metadata, domains))
    vector_scores = {
        str(document.metadata["policy_id"]): float(score)
        for document, score in vector_pairs
        if _domain_allowed(document.metadata, domains)
    }
    keyword_scores: dict[str, float] = {}
    for document in index.documents:
        if not _domain_allowed(document.metadata, domains):
            continue
        score = _keyword_score(plan["rewritten_query"], document.page_content)
        if score > 0:
            policy_id = str(document.metadata["policy_id"])
            keyword_scores[policy_id] = max(keyword_scores.get(policy_id, 0.0), score)
    log_course_event(
        "RAG_DUAL_RECALL",
        "向量召回与关键词召回已分别完成",
        teaching=True,
        vector_candidates={key: round(value, 3) for key, value in vector_scores.items()},
        keyword_candidates={key: round(value, 3) for key, value in keyword_scores.items()},
        allowed_domains=sorted(domains),
    )

    merged_ids = set(vector_scores) | set(keyword_scores)
    ranked: list[tuple[str, float, list[str]]] = []
    for policy_id in merged_ids:
        vector_score = vector_scores.get(policy_id, 0.0)
        keyword_score = keyword_scores.get(policy_id, 0.0)
        score = max(vector_score, keyword_score) + (0.08 if vector_score and keyword_score else 0.0)
        reasons = []
        if vector_score:
            reasons.append("vector召回")
        if keyword_score:
            reasons.append("keyword召回")
        ranked.append((policy_id, round(min(1.0, score), 3), reasons))
    ranked.sort(key=lambda item: item[1], reverse=True)

    filename_by_policy = {
        str(document.metadata["policy_id"]): str(document.metadata["filename"])
        for document in index.documents
    }
    citations: list[Citation] = []
    source_scores: dict[str, Any] = {}
    for policy_id, score, reasons in ranked[:top_k]:
        citation = load_knowledge_citation(filename_by_policy[policy_id])
        citations.append(citation.model_copy(update={"score": score}))
        source_scores[policy_id] = {
            "vector": round(vector_scores.get(policy_id, 0.0), 3),
            "keyword": round(keyword_scores.get(policy_id, 0.0), 3),
            "final": score,
            "sources": reasons,
        }
    log_course_event(
        "RAG_FUSION_RANKED",
        "双路候选已融合并按最终得分排序",
        teaching=True,
        fusion_rule="max(vector, keyword) + 双路命中加分0.08",
        top_k=top_k,
        ranking=source_scores,
    )
    result = HybridRetrievalResult(
        citations=citations,
        debug={
            "mode": "langchain_inmemory_hybrid",
            "embedding": index.embedding_mode,
            "plan": plan,
            "index_version": index.version,
            "index_chunk_count": len(index.documents),
            "index_cache_hit": index_cache_hit,
            "retrieval_cache_hit": False,
            "cache_key": cache_key,
            "vector_policy_ids": list(vector_scores),
            "keyword_policy_ids": list(keyword_scores),
            "source_scores": source_scores,
        },
    )
    RAG_RETRIEVAL_CACHE[cache_key] = result
    return result


def reset_hybrid_index_and_cache() -> None:
    global _KNOWLEDGE_INDEX
    _KNOWLEDGE_INDEX = None
    RAG_RETRIEVAL_CACHE.clear()


def _domain_allowed(metadata: dict[str, Any], domains: set[str]) -> bool:
    if not domains:
        return True
    knowledge_domain = str(metadata.get("knowledge_domain") or "")
    if knowledge_domain:
        return knowledge_domain in domains
    scene_key = str(metadata.get("scene_key") or "")
    mapping = {
        "promotion": "promotion",
        "member_coupon": "member_coupon",
        "invoice": "invoice",
        "payment_invoice": "invoice",
        "after_sale": "after_sale",
    }
    return mapping.get(scene_key, scene_key) in domains


def _keyword_score(query: str, text: str) -> float:
    normalized_text = normalize_query(text)
    business_terms = {
        term
        for term in (
            "618",
            "大促",
            "满减",
            "300减40",
            "会员券",
            "金卡",
            "叠加",
            "电子发票",
            "发票",
            "24小时",
            "退款",
            "未发货",
        )
        if term in query
    }
    chinese_bigrams = {
        query[index : index + 2]
        for index in range(max(0, len(query) - 1))
        if re.fullmatch(r"[\u4e00-\u9fff]{2}", query[index : index + 2])
    }
    terms = business_terms | chinese_bigrams | set(re.findall(r"[a-z0-9]+", query))
    matched = [term for term in terms if term in normalized_text]
    return round(min(1.0, len(matched) / max(1, len(terms)) + (0.15 if matched else 0.0)), 3)
