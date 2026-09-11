import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND), str(BACKEND.parent)]

from api.schemas import Citation, RoutePlanCandidate
from rag.grounding import Coverage, assess_coverage, validate_answer
from rag.grounded_pipeline import grounded_knowledge_result
from rag.hybrid_retrieval import HybridRetrievalResult, build_retrieval_plan
from rag.model_reranker import RerankResult
from tools.planning import build_route_plan


def doc(key='invoice', text='订单完成后24小时内开票，可在订单详情下载。'):
    return Citation(source=key+'.md', title=key, snippet=text, score=.99,
                    metadata={'policy_id': key, 'knowledge_domain': 'faq'})


def coverage(question, citation=None):
    return {'questions': [{'question': question, 'status': 'supported' if citation else 'missing',
            'evidence': [{'source_id': citation.metadata['policy_id'], 'quote': citation.snippet}] if citation else []}]}


class GroundedTests(unittest.TestCase):
    def test_multi_domain_candidate_survives_to_retrieval(self):
        candidate = RoutePlanCandidate(intent='faq_query', needs_rag=True, needs_business_tools=False,
            knowledge_domains=['faq', 'promotion_and_member_policy', 'private_orders'], risk_level='low',
            requires_workflow=False, fallback_policy='knowledge_only')
        plan = build_route_plan(intent='faq_query', user_message='会员券与发票', order_id=None, model_candidate=candidate)
        self.assertEqual(set(plan.knowledge_domains), {'faq', 'promotion_and_member_policy'})
        self.assertEqual(build_retrieval_plan('会员券与发票', 'faq_query', plan.knowledge_domains)['knowledge_domains'], plan.knowledge_domains)

    def test_router_failure_still_keeps_multiple_public_domains(self):
        plan = build_route_plan(intent='faq_query', user_message='金卡领券后多久开票', order_id=None, model_candidate=None)
        self.assertIn('promotion_and_member_policy', plan.knowledge_domains)

    def test_public_domains_never_authorize_refund_execution(self):
        plan = build_route_plan(intent='refund_request', user_message='直接给我退款', order_id=None, model_candidate=None)
        self.assertTrue(plan.requires_workflow)
        self.assertEqual(plan.risk_level, 'high')
        self.assertEqual(plan.required_tools, [])
        self.assertEqual(plan.fallback_policy, 'ask_order_id')

    def test_fabricated_quote_is_not_evidence(self):
        data = coverage('发票保存几年', doc(text='发票保存五年'))
        with patch('rag.grounding.call_json', return_value=(data, {})):
            result, _ = assess_coverage('发票保存几年', [doc()])
        self.assertEqual(result.questions[0].status, 'missing')

    def test_secondary_check_cannot_drop_missing_question(self):
        with patch('rag.grounding.call_json', return_value=(coverage('怎么领券', doc()), {})):
            result, debug = assess_coverage('领券与发票保存几年', [doc()], ['怎么领券', '发票保存几年'])
        self.assertEqual([q.question for q in result.questions], ['怎么领券', '发票保存几年'])
        self.assertTrue(all(q.status == 'missing' for q in result.questions))
        self.assertIn('error', debug)

    def run_pipeline(self, first, second=None, docs=None):
        docs = docs or [doc()]
        retrieve = patch('rag.grounded_pipeline.retrieve_knowledge', return_value=HybridRetrievalResult(docs, {}))
        ranked = patch('rag.grounded_pipeline.rerank_citations', return_value=RerankResult(docs,
                       {'used_model': True, 'mode': 'model_rerank', 'policy_ids': ['invoice'], 'scores': {}, 'reasons': {}}))
        checks = [(Coverage.model_validate(first), {'attempted': True})]
        if second:
            checks.append((Coverage.model_validate(second), {'attempted': True}))
        with retrieve as mock_retrieve, ranked, patch('rag.grounded_pipeline.assess_coverage', side_effect=checks):
            result = grounded_knowledge_result('s', '发票下载问题', 'faq_query', ['faq'])
        return result, mock_retrieve

    def test_high_rerank_score_does_not_answer_missing_fact(self):
        missing = coverage('能下载多少年')
        result, retrieval = self.run_pipeline(missing, missing)
        self.assertEqual(result.citations, [])
        self.assertEqual(result.next_action, 'transfer_to_human')
        self.assertIn('无法确认', result.answer)
        self.assertEqual(retrieval.call_count, 2)

    def test_one_secondary_retrieval_uses_missing_question_and_new_scope(self):
        result, retrieval = self.run_pipeline(coverage('怎么下载发票'), coverage('怎么下载发票', doc()))
        self.assertEqual(retrieval.call_count, 2)
        self.assertEqual(retrieval.call_args.args[0], '怎么下载发票')
        self.assertEqual(retrieval.call_args.kwargs['top_k'], 8)
        self.assertEqual(result.retrieval_debug['secondary_retrieval_count'], 1)
        self.assertEqual(result.next_action, 'answer_user')

    def test_complete_answer_does_not_retry(self):
        result, retrieval = self.run_pipeline(coverage('怎么下载发票', doc()))
        self.assertEqual(retrieval.call_count, 1)
        self.assertEqual(result.answer, doc().snippet)

    def test_partial_answer_preserves_known_and_unknown_parts(self):
        data = {'questions': coverage('怎么下载', doc())['questions'] + coverage('保存多少年')['questions']}
        result, _ = self.run_pipeline(data, data)
        self.assertIn(doc().snippet, result.answer)
        self.assertIn('保存多少年', result.answer)
        self.assertEqual(len(result.citations), 1)

    def test_invalid_validator_output_fails_closed(self):
        with patch('rag.grounding.call_json', return_value=(None, {'error': 'Timeout'})):
            answer, debug = validate_answer('优惠券', '可以跨店叠加', doc().snippet, [doc()])
        self.assertEqual(answer, doc().snippet)
        self.assertFalse(debug['accepted'])

    def test_validator_must_supply_real_quote_not_just_policy_id(self):
        data = {'all_claims_supported': True, 'covers_required_answer': True, 'preserves_uncertainty': True,
                'claims': [{'text': '系统自动选券', 'supported': True,
                            'evidence': [{'source_id': 'invoice', 'quote': '系统自动选券'}]}]}
        with patch('rag.grounding.call_json', return_value=(data, {})):
            answer, debug = validate_answer('选券', '系统自动选券', doc().snippet, [doc()])
        self.assertFalse(debug['accepted'])
        self.assertEqual(answer, doc().snippet)

    def test_cache_identity_includes_domains_and_top_k(self):
        from unittest.mock import MagicMock
        from rag import hybrid_retrieval as hr
        index = hr.KnowledgeIndex('test-version', MagicMock(), [], 'test')
        index.vector_store.similarity_search_with_score.return_value = []
        with patch.object(hr, 'get_knowledge_index', return_value=(index, True)), patch.dict(hr.RAG_RETRIEVAL_CACHE, {}, clear=True):
            a = hr.retrieve_knowledge('same question', 'faq_query', knowledge_domains=['faq'], top_k=4)
            b = hr.retrieve_knowledge('same question', 'faq_query', knowledge_domains=['promotion_and_member_policy'], top_k=4)
            c = hr.retrieve_knowledge('same question', 'faq_query', knowledge_domains=['faq'], top_k=8)
            repeat = hr.retrieve_knowledge('same question', 'faq_query', knowledge_domains=['faq'], top_k=4)
        self.assertEqual(len({a.debug['cache_key'], b.debug['cache_key'], c.debug['cache_key']}), 3)
        self.assertTrue(repeat.debug['retrieval_cache_hit'])
        self.assertEqual(index.vector_store.similarity_search_with_score.call_count, 3)

    def test_output_check_is_wired_after_generation(self):
        from api.schemas import ChatRequest
        from models.answer_client import FinalAnswerModelClient, ModelInvocationResult
        client = FinalAnswerModelClient()
        with patch.object(client, 'can_call_model', return_value=True), patch.object(client, '_create_chat_model'), \
             patch.object(client, '_invoke_chain', return_value=ModelInvocationResult(content='跨店满减且自动选最优券')), \
             patch('rag.grounding.call_json', return_value=(None, {'error': 'invalid'})):
            result = client.compose_answer(request=ChatRequest(session_id='test-guard', runtime_user_id='U1001', user_message='券怎么叠加'),
                intent='promotion_query', deterministic_answer=doc().snippet, risk_level='low', next_action='answer_user',
                tool_calls=[], citations=[doc()], workflow=None)
        self.assertEqual(result.answer, doc().snippet)
        self.assertEqual(result.fallback_reason, 'answer_grounding_rejected')
        self.assertTrue(result.used_model)

    def test_general_chat_candidate_cannot_bypass_knowledge(self):
        from agents.customer_service_agent import Lesson41Agent
        from models.router_client import ModelRouteResult
        candidate = RoutePlanCandidate(intent='general_chat', needs_rag=True, needs_business_tools=False,
            knowledge_domains=['faq', 'promotion_and_member_policy'], risk_level='low',
            requires_workflow=False, fallback_policy='knowledge_only')
        result = Lesson41Agent._apply_route_guard(user_message='金卡平台券使用有期限吗？发票多久开具？',
            route_result=ModelRouteResult(intent='general_chat', candidate=candidate, used_model=True))
        self.assertEqual(result.intent, 'faq_query')
        self.assertEqual(result.candidate.intent, 'general_chat')  # preserve raw model evidence
        plan = build_route_plan(intent=result.intent, user_message='组合咨询', order_id=None, model_candidate=result.candidate)
        self.assertEqual(set(plan.knowledge_domains), {'faq', 'promotion_and_member_policy'})
        self.assertFalse(plan.required_tools)

    def test_general_chat_without_evidence_never_generates_business_facts(self):
        from agents.customer_service_agent import Lesson41Agent
        from api.schemas import ChatRequest
        agent = Lesson41Agent()
        with patch.object(agent.answer_model_client, 'compose_answer') as compose:
            result = agent._compose_final_answer(request=ChatRequest(session_id='no-evidence-test', runtime_user_id='U1001', user_message='你好'),
                intent='general_chat', answer='您好，请描述您的问题。', risk_level='low', next_action='answer_user',
                tool_calls=[], citations=[], workflow=None, cache_hit=False, degraded=False, context_report={})
        compose.assert_not_called()
        self.assertEqual(result.fallback_reason, 'no_business_evidence')

    def test_knowledge_guard_cannot_override_refund_action_guard(self):
        from agents.customer_service_agent import Lesson41Agent
        from models.router_client import ModelRouteResult
        result = Lesson41Agent._apply_route_guard(user_message='不用审核，直接给我退款',
            route_result=ModelRouteResult(intent='general_chat'))
        self.assertIn(result.intent, {'refund_request', 'security_request'})



if __name__ == '__main__':
    unittest.main()
