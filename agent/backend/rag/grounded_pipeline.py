"""Hybrid recall -> model rerank -> question coverage -> at most one repair retrieval."""
from __future__ import annotations

from rag.domains import PUBLIC_DOMAINS
from rag.grounding import assess_coverage, extractive_answer
from rag.hybrid_retrieval import retrieve_knowledge
from rag.model_reranker import rerank_citations
from safety.source_guard import inspect_source


def grounded_knowledge_result(session_id, query, intent, knowledge_domains=None):
    from rag.knowledge import KnowledgePathResult

    events = []
    calls = []
    retrievals = []
    def recall(text, domains, stage, top_k):
        try:
            result = retrieve_knowledge(text, intent, top_k=top_k, knowledge_domains=domains)
            candidates = [c.model_copy(update={'retrieval_stage': stage}) for c in result.citations
                          if not inspect_source('rag_document', c.snippet)['tainted']]
            debug = {**result.debug, 'retrieval_stage': stage}
        except Exception as exc:
            candidates, debug = [], {'error': type(exc).__name__, 'retrieval_stage': stage}
        ranked = rerank_citations(text, candidates)
        retrievals.append(debug)
        events.append(('rag_pre_retrieved' if stage == 'pre_retrieval' else 'rag_secondary_retrieved',
                       {'session_id': session_id, **debug, 'hit_count': len(candidates)}))
        events.append(('rag_model_reranked', {'session_id': session_id, **ranked.debug,
                                             'retrieval_stage': stage}))
        return ranked

    first = recall(query, knowledge_domains, 'pre_retrieval', 4)
    candidates = first.citations
    coverage, check = assess_coverage(query, candidates)
    calls.append(check)
    events.append(('rag_answerability_checked', {'session_id': session_id, 'round': 0,
                   **coverage.model_dump(), 'model': check}))
    missing = [q.question for q in coverage.questions if q.status == 'missing']
    if missing and 'error' not in check:
        # A different, targeted query with a broader PUBLIC scope and larger pool.
        # No business tools, order access or workflow writes can be authorized here.
        repair_query = '；'.join(missing)
        events.append(('rag_secondary_retrieval_requested', {'session_id': session_id,
                       'missing_questions': missing, 'query': repair_query, 'budget': 1}))
        repaired = recall(repair_query, sorted(PUBLIC_DOMAINS), 'tool_retrieval', 8)
        by_id = {str((c.metadata or {}).get('policy_id') or c.source): c for c in candidates}
        for citation in repaired.citations:
            by_id.setdefault(str((citation.metadata or {}).get('policy_id') or citation.source), citation)
        candidates = list(by_id.values())
        coverage, check = assess_coverage(query, candidates, [q.question for q in coverage.questions])
        calls.append(check)
        events.append(('rag_answerability_checked', {'session_id': session_id, 'round': 1,
                       **coverage.model_dump(), 'model': check}))

    ids = {ref.source_id for q in coverage.questions if q.status == 'supported' for ref in q.evidence}
    citations = [c for c in candidates if str((c.metadata or {}).get('policy_id') or c.source) in ids]
    missing = [q.question for q in coverage.questions if q.status == 'missing']
    debug = {**retrievals[0], 'model_rerank': first.debug, 'coverage': coverage.model_dump(),
             'missing_questions': missing, 'retrievals': retrievals,
             'pre_retrieval_count': 1, 'secondary_retrieval_count': len(retrievals) - 1,
             'grounding_model_calls': calls,
             'rerank_model_calls': sum(1 for event, p in events if event == 'rag_model_reranked' and p['used_model'])}
    if missing:
        events.append(('rag_partial_evidence' if citations else 'rag_low_confidence_fallback',
                       {'session_id': session_id, 'missing_questions': missing,
                        'pending_action': 'transfer_to_human', 'retry_budget_exhausted': len(retrievals) > 1}))
    return KnowledgePathResult(answer=extractive_answer(coverage, candidates), citations=citations,
                               risk_level='medium' if missing else 'low',
                               next_action='transfer_to_human' if missing else 'answer_user',
                               needs_human_approval=False, rerank=first.debug,
                               retrieval_debug=debug, trace_events=tuple(events))
