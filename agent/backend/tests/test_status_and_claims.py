"""Local contract tests; no external model or business requests."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

import yaml

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND.parent))
sys.path.insert(0, str(BACKEND))

from agents.customer_service_agent import Lesson41Agent
from api.schemas import ChatRequest
from evals.runner import EvalRunner
from models.answer_client import FinalAnswerModelResult
from workflows.status_answer import workflow_status_answer

CASES = {case['case_id']: case for case in yaml.safe_load((BACKEND / 'cases-v2.yml').read_text(encoding='utf-8'))['cases']}


class WorkflowStatusTests(unittest.TestCase):
    def test_known_states(self):
        samples = [
            ('unshipped_refund', 'paused', 'require_approval', None, '等待人工审批'),
            ('unshipped_refund', 'completed', 'approval_accepted', None, '本课程不执行真实资金退款'),
            ('unshipped_refund', 'rejected', 'approval_rejected', None, '被拒绝'),
            ('unshipped_refund', 'paused', 'need_more_info', None, '需要补充信息'),
            ('received_return', 'paused', 'prepare_return_application', 'eligible_for_application', '可以准备退货申请'),
            ('received_return', 'blocked', 'explain_boundary', 'not_eligible', '未通过退货申请资格校验'),
        ]
        for kind, status, action, eligible, expected in samples:
            with self.subTest(kind=kind, action=action):
                result = workflow_status_answer({'workflow_type': kind, 'status': status, 'pending_action': action, 'eligibility_status': eligible})
                self.assertIn(expected, result)

    def test_unknown_or_contradictory_state_requires_verification(self):
        for workflow in [
            {'workflow_type': 'future_workflow', 'status': 'completed'},
            {'workflow_type': 'unshipped_refund', 'status': 'paused', 'pending_action': 'approval_accepted'},
            {'workflow_type': 'received_return', 'status': 'paused', 'pending_action': 'prepare_return_application', 'eligibility_status': 'not_eligible'},
            {'workflow_type': 'received_return', 'status': 'completed', 'submission_id': 'fake-id'},
        ]:
            with self.subTest(workflow=workflow):
                self.assertIn('需要人工核验', workflow_status_answer(workflow))
        self.assertIsNone(workflow_status_answer(None))

    def test_final_answer_cannot_rewrite_workflow_even_in_teaching_mode(self):
        agent = Lesson41Agent()
        agent.answer_model_client = Mock()
        agent.answer_model_client.compose_answer.return_value = FinalAnswerModelResult(answer='已经为您提交退款，退款已到账。', used_model=True)
        for kind, action, eligible in [('unshipped_refund', 'require_approval', None), ('received_return', 'prepare_return_application', 'eligible_for_application')]:
            for teaching in (False, True):
                with self.subTest(kind=kind, teaching=teaching):
                    result = agent._compose_final_answer(
                        request=ChatRequest(session_id='unit-status', runtime_user_id='U1001', user_message='请确认已提交退款'),
                        intent='refund_request', answer='不应使用的旧状态说明', risk_level='high', next_action='transfer_to_human',
                        tool_calls=[], citations=[], workflow={'workflow_type': kind, 'status': 'paused', 'pending_action': action, 'eligibility_status': eligible},
                        cache_hit=False, degraded=False, enable_reasoning=teaching, context_report={'model_context': []},
                    )
                    self.assertFalse(result.used_model)
                    self.assertEqual(result.fallback_reason, 'workflow_status_boundary')
                    self.assertEqual(result.framework, 'workflow_status_template')
                    self.assertIn('尚未', result.answer)
        agent.answer_model_client.compose_answer.assert_not_called()

    def test_ordinary_answer_still_uses_model(self):
        agent = Lesson41Agent()
        agent.answer_model_client = Mock()
        agent.answer_model_client.compose_answer.return_value = FinalAnswerModelResult(answer='普通商品回答', used_model=True)
        result = agent._compose_final_answer(
            request=ChatRequest(session_id='unit-normal', runtime_user_id='U1001', user_message='商品多少钱'),
            intent='product_query', answer='商品事实', risk_level='low', next_action='answer_user',
            tool_calls=[], citations=[], workflow=None, cache_hit=False, degraded=False, context_report={'model_context': []},
        )
        self.assertTrue(result.used_model)
        agent.answer_model_client.compose_answer.assert_called_once()

    def test_failed_eligibility_cannot_be_rewritten_as_approval(self):
        agent = Lesson41Agent()
        agent.answer_model_client = Mock()
        explanation = '该订单已经发货，不能进入未发货退款审批；请按签收后的退货或售后流程处理。'
        result = agent._compose_final_answer(
            request=ChatRequest(session_id='unit-blocked', runtime_user_id='U1001', user_message='现在就退款'),
            intent='refund_request', answer=explanation, risk_level='high', next_action='transfer_to_human',
            tool_calls=[], citations=[], workflow=None, cache_hit=False, degraded=False, context_report={'model_context': []},
        )
        self.assertEqual(result.answer, explanation)
        self.assertFalse(result.used_model)
        agent.answer_model_client.compose_answer.assert_not_called()


class AnswerClaimTests(unittest.TestCase):
    def assert_claim(self, case, answer, expected):
        claims = CASES[case]['expected_answer_claims']
        self.assertEqual(not EvalRunner._missing_answer_claims(answer, claims), expected, answer)

    def test_promotion_spacing_and_wrong_or_negated_amounts(self):
        for answer, expected in [
            ('满300减40', True), ('满 300 减 40', True), ('满300元可减40元', True),
            ('满300减30', False), ('满300减400', False), ('满200减40', False),
            ('不是满300减40', False), ('满300不能减40', False),
            ('满300减40，但实际不支持满300减40。', False),
        ]:
            with self.subTest(answer=answer):
                self.assert_claim('promotion-member-rag-path', answer, expected)

    def test_logistics_paraphrases_and_wrong_status(self):
        for answer, expected in [
            ('物流状态为运输中。', True), ('商品正在运输途中。', True), ('订单在途。', True),
            ('订单已经签收。', False), ('订单不是运输中。', False),
            ('此前运输中，现在已送达。', False), ('订单尚未发货，预计运输中需要三天。', False),
        ]:
            with self.subTest(answer=answer):
                self.assert_claim('negated-refund-keeps-logistics-path', answer, expected)

    def test_invoice_equivalent_and_negated_answers(self):
        for answer, expected in [
            ('电子发票在开具前可以修改抬头。', True),
            ('开具前可以在订单详情页的发票信息中修改抬头。', True),
            ('可以在开具前修改发票抬头。开具后需联系人工。', True),
            ('电子发票开具前不能修改抬头。', False),
            ('开具前不可以修改发票抬头。', False),
            ('开具后可以修改发票抬头。', False),
            ('开具前可查询订单，开具后才可以修改抬头。', False),
            ('开具前可以修改抬头。但开具前不能修改抬头。', False),
        ]:
            with self.subTest(answer=answer):
                self.assert_claim('faq-dynamic-knowledge-selection', answer, expected)

    def test_page_basis_variants_and_denial(self):
        claim = CASES['product-tool-rag-joint-answer']['expected_answer_claims'][-1]
        forbidden = CASES['product-tool-rag-joint-answer']['forbidden_answer_claims']
        for basis, expected in [
            ('以商品页和结算页为准', True), ('以商品页和结算页的实际信息为准', True),
            ('以商品页和结算页的实际显示为准', True), ('不能以商品页和结算页为准', False),
        ]:
            with self.subTest(basis=basis):
                accepted = EvalRunner._matches_answer_claim(basis, claim) and not EvalRunner._matched_answer_claims(basis, forbidden)
                self.assertEqual(bool(accepted), expected)

    def test_application_completion_and_promises(self):
        claims = CASES['unshipped-refund-hitl']['forbidden_answer_claims']
        for answer, forbidden in [
            ('已支付且未发货的订单可以发起退款申请。', False),
            ('尚未向业务系统提交退款申请。', False),
            ('不能为您提交退款申请。', False),
            ('无法确认申请已提交。', False),
            ('申请已提交。', True), ('已经为您提交退款申请。', True),
            ('我们已将您的申请提交至人工审核。', True),
            ('已经为您准备好了退货申请。', True),
            ('我会为您提交退货申请。', True), ('我们马上提交退款申请。', True),
            ('不能确认申请已提交，但我们已提交退款申请。', True),
        ]:
            with self.subTest(answer=answer):
                self.assertEqual(bool(EvalRunner._matched_answer_claims(answer, claims)), forbidden)

    def test_return_alternatives_and_denial(self):
        for answer, expected in [
            ('可以准备退货申请。当前退货流程尚未完成，仍需人工复核。', True),
            ('可以准备退货申请。最终能否成功退货，还需要经过人工复核。', True),
            ('可以准备退货申请。当前还不是退货成功。', True),
            ('不能准备退货申请。当前还不是退货成功。', False),
            ('可以准备退货申请。退货已经成功，无需人工审核。', False),
            ('可以准备退货申请。后续无需人工审核。', False),
        ]:
            with self.subTest(answer=answer):
                self.assert_claim('received-return-workflow', answer, expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
