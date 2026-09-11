"""读取第 41 课真实知识文件，并转换成公开 Citation 契约。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from api.schemas import Citation


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"


@lru_cache(maxsize=None)
def load_knowledge_citation(name: str) -> Citation:
    """按 YAML frontmatter 解析知识文件，让 citation 指向真实可替换材料。"""
    path = (KNOWLEDGE_DIR / name).resolve()
    if path.parent != KNOWLEDGE_DIR:
        raise ValueError(f"Invalid knowledge name: {name}")
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise ValueError(f"Knowledge file must start with YAML frontmatter: {path}")
    frontmatter, separator, body = raw[4:].partition("\n---\n")
    if not separator:
        raise ValueError(f"Knowledge file has incomplete YAML frontmatter: {path}")
    metadata: dict[str, Any] = yaml.safe_load(frontmatter) or {}
    citation_metadata: dict[str, Any] = {
        "policy_id": str(metadata["policy_id"]),
        "scene_key": str(metadata["scene_key"]),
    }
    # 这些字段由知识文件声明，供通用检索、证据门和缓存治理使用。
    for key in ("knowledge_domain", "knowledge_version", "cache_scope"):
        if key in metadata:
            citation_metadata[key] = str(metadata[key])
    return Citation(
        source=f"knowledge/{name}",
        title=str(metadata["title"]),
        snippet=body.strip(),
        score=float(metadata["score"]),
        retrieval_stage=metadata.get("retrieval_stage"),
        metadata=citation_metadata,
    )
