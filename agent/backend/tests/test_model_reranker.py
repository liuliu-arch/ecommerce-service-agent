import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.schemas import Citation
from rag.hybrid_retrieval import HybridRetrievalResult
from rag.model_reranker import model_knowledge_result, rerank_citations


def citation(policy, text):
    return Citation(source=policy + '.md', title=policy, snippet=text, score=0.7,
                    metadata={'policy_id': policy, 'knowledge_domain': 'faq'})


class ModelRerankerTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'AGENT_RAG_RERANK_ENABLED': 'true',
            'AGENT_RAG_RERANK_MODEL': 'Qwen/Qwen3-Reranker-8B',
            'AGENT_RAG_RERANK_BASE_URL': 'https://example.test/v1',
            'AGENT_OPENAI_BASE_URL': 'https://example.test/v1',
            'AGENT_OPENAI_API_KEY': 'unit-test-secret',
            'AGENT_RAG_RERANK_API_KEY': '',
            'AGENT_RAG_RERANK_MIN_SCORE': '0.5',
            'AGENT_RAG_RERANK_TIMEOUT_SECONDS': '15',
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.loader = patch('rag.model_reranker.load_course_env')
        self.loader.start()
        self.addCleanup(self.loader.stop)
        self.client = patch('rag.model_reranker.httpx.Client').start()
        self.addCleanup(patch.stopall)
        self.post = self.client.return_value.__enter__.return_value.post
        self.docs = [citation('title', '已开具发票修改抬头需要人工核验。'),
                     citation('issue', '订单完成后24小时内开票，可在订单详情下载。')]

    def reply(self, items, status=200):
        self.post.return_value = httpx.Response(status, json={'results': items},
            request=httpx.Request('POST', 'https://example.test/v1/rerank'))

    def test_indexes_preserve_correct_source_and_original_score(self):
        self.reply([{'index': 1, 'relevance_score': .92}, {'index': 0, 'relevance_score': .1}])
        result = rerank_citations('发票在哪下载？', self.docs)
        self.assertEqual([c.source for c in result.citations], ['issue.md', 'title.md'])
        self.assertEqual(result.citations[0].metadata['retrieval_score'], .7)
        self.assertEqual(self.docs[0].score, .7)
        self.assertEqual(self.post.call_args.kwargs['json']['documents'], [c.snippet for c in self.docs])

    def test_multi_question_keeps_both_and_never_skips_generation_via_policy_cache(self):
        self.reply([{'index': 1, 'relevance_score': .92}, {'index': 0, 'relevance_score': .88}])
        result, event = model_knowledge_result('s', '多久开票？抬头错了怎么办？', HybridRetrievalResult(self.docs, {}), 'faq_query')
        self.assertEqual(len(result.citations), 2)
        self.assertFalse(result.cache_hit)
        self.assertEqual(event[1]['selected_policy_ids'], ['issue', 'title'])

    def test_single_promotion_evidence_is_sufficient_when_ranked_relevant(self):
        self.reply([{'index': 0, 'relevance_score': .95}])
        result, _ = model_knowledge_result('s', '同类满减券能叠加吗？', HybridRetrievalResult(self.docs[:1], {}), 'promotion_query')
        self.assertEqual(result.next_action, 'answer_user')

    def test_low_scores_do_not_fall_back_to_high_retrieval_scores(self):
        self.reply([{'index': 0, 'relevance_score': .1}, {'index': 1, 'relevance_score': .2}])
        result, _ = model_knowledge_result('s', '手续费多少？', HybridRetrievalResult(self.docs, {}), 'faq_query')
        self.assertEqual(result.citations, [])
        self.assertEqual(result.next_action, 'transfer_to_human')

    def test_timeout_preserves_candidates_and_does_not_leak_exception(self):
        self.post.side_effect = httpx.ReadTimeout('unit-test-secret')
        result = rerank_citations('下载', self.docs)
        self.assertEqual(result.citations, self.docs)
        self.assertEqual(result.debug['fallback_reason'], 'ReadTimeout')
        self.assertNotIn('unit-test-secret', str(result.debug))

    def test_http_failure_records_only_status(self):
        self.reply([], 401)
        self.assertEqual(rerank_citations('下载', self.docs).debug['fallback_reason'], 'http_401')

    def test_invalid_provider_results_do_not_partially_replace_ranking(self):
        bad_results = [
            [{'index': 0, 'relevance_score': .9}],
            [{'index': 0, 'relevance_score': .9}, {'index': 0, 'relevance_score': .8}],
            [{'index': 2, 'relevance_score': .9}, {'index': 0, 'relevance_score': .8}],
            [{'index': 0, 'relevance_score': 2}, {'index': 1, 'relevance_score': .8}],
        ]
        for items in bad_results:
            with self.subTest(items=items):
                self.reply(items)
                result = rerank_citations('下载', self.docs)
                self.assertFalse(result.debug['used_model'])
                self.assertEqual(result.citations, self.docs)

    def test_disabled_does_not_call_provider(self):
        with patch.dict(os.environ, {'AGENT_RAG_RERANK_ENABLED': 'false'}):
            self.assertEqual(rerank_citations('下载', self.docs).debug['fallback_reason'], 'disabled')
        self.post.assert_not_called()

    def test_empty_candidates_do_not_call_provider(self):
        self.assertEqual(rerank_citations('下载', []).debug['fallback_reason'], 'no_candidates')
        self.post.assert_not_called()

    def test_other_provider_cannot_reuse_chat_key(self):
        with patch.dict(os.environ, {'AGENT_RAG_RERANK_BASE_URL': 'https://other.test/v1'}):
            self.assertEqual(rerank_citations('下载', self.docs).debug['fallback_reason'], 'separate_provider_key_required')
        self.post.assert_not_called()

    def test_chat_summary_accepts_model_rerank_contract(self):
        from agents.customer_service_agent import Lesson41Agent
        from api.schemas import ChatRequest
        self.reply([{'index': 1, 'relevance_score': .92}, {'index': 0, 'relevance_score': .1}])
        with patch.dict(os.environ, {'AGENT_COURSE_DISABLE_LLM': '1'}), patch(
            'rag.grounded_pipeline.retrieve_knowledge', return_value=HybridRetrievalResult(self.docs, {'index_version': 'test'})
        ):
            response = Lesson41Agent().chat(ChatRequest(session_id='rerank-contract-test', runtime_user_id='U1001', user_message='电子发票怎么下载？'))
        self.assertEqual(response.session_state['rag']['rerank_mode'], 'model_rerank')
        self.assertEqual(response.session_state['rag']['citation_ids'], [])
        self.assertEqual(response.session_state['next_action'], 'transfer_to_human')


if __name__ == '__main__':
    unittest.main()
