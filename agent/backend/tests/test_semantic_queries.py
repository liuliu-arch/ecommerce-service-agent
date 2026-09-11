import unittest
from unittest.mock import patch
from decimal import Decimal
from api.schemas import ChatRequest
from tools.query_plan import QueryPlan, remember_plan, model_context
from tools.read_queries import list_orders, product_answer, resolve_products, detail_answer
from context.builder import SESSION_MEMORIES
from models.router_client import RouteModelClient

class SemanticQueries(unittest.TestCase):
    def request(self,orders=None,**kw):
        return ChatRequest(session_id='semantic-unit',runtime_user_id='U1001',user_message='口语问题无需再正则匹配',runtime_context={'currentUserOrders':orders or [],'currentUserOrdersTruncated':False},**kw)
    def test_bounds_and_identity_are_validated(self):
        for extra in [{'date_from':'2026-06-03','date_to':'2026-06-01'},{'amount_min':30,'amount_max':20},{'user_id':'U1002'},{'order_ids':['made-up']},{'scope':'specific'}]:
            with self.assertRaises(ValueError):QueryPlan(normalized_question='查订单',target='orders',**extra)
    def test_filter_and_sum_with_exact_decimal(self):
        orders=[{'orderNo':f'SO2026060{i}-abc','createdAt':f'2026-06-0{i}T12:00:00','totalAmount':amount,'status':'SHIPPED','itemSummary':['耳机']} for i,amount in [(1,'0.10'),(2,'0.20'),(3,'0.40'),(4,'0.90')]]
        plan=QueryPlan(normalized_question='查询并计算',target='orders',scope='collection',date_from='2026-06-01',date_to='2026-06-03',amount_min='0.10',min_inclusive=False,operations=['list','sum'])
        answer,call=list_orders(self.request(orders),plan)
        self.assertIn('0.6 元',answer);self.assertEqual(call.arguments['count'],2)
        self.assertNotIn('SO20260601-',answer);self.assertNotIn('SO20260604-',answer)
    def test_foreign_owner_filtered(self):
        answer,call=list_orders(self.request([{'orderNo':'SO123-abc','userId':'U1002','totalAmount':123}]),QueryPlan(normalized_question='全部',target='orders',scope='collection'))
        self.assertEqual(call.arguments['count'],0);self.assertNotIn('123 元',answer)
    def test_plan_memory_owner_isolation(self):
        SESSION_MEMORIES.pop('semantic-unit',None)
        plan=QueryPlan(normalized_question='六月耳机',target='orders',scope='collection',date_from='2026-06-01',date_to='2026-06-30',product_terms=['耳机'])
        remember_plan(self.request(),plan)
        self.assertEqual(model_context(self.request())['previous_query']['date_from'],'2026-06-01')
        other=self.request().model_copy(update={'runtime_user_id':'U1002'})
        self.assertIsNone(model_context(other)['previous_query'])
    def test_product_budget_really_filters(self):
        catalog=[{'name':'65W GaN 快充充电器','price':199,'stock':2,'active':True},{'name':'100W 充电器','price':299,'stock':5,'active':True}]
        plan=QueryPlan(normalized_question='两百以内',target='products',product_terms=['充电器'],amount_max=200,in_stock=True)
        with patch('tools.read_queries.ecommerce_get',return_value=catalog):answer,call,_=product_answer(self.request(),plan)
        self.assertEqual(call.arguments['product_names'],['65W GaN 快充充电器'])
    def test_product_ambiguity_and_unknown(self):
        catalog=[{'name':'轻量蓝牙耳机A'},{'name':'轻量蓝牙耳机B'}]
        selected,ambiguous=resolve_products(['轻量蓝牙耳机'],catalog)
        self.assertFalse(selected);self.assertEqual(len(ambiguous),2)
        selected,ambiguous=resolve_products(['不存在的量子传送门'],catalog)
        self.assertFalse(selected);self.assertFalse(ambiguous)
    def test_logistics_not_found_does_not_erase_order(self):
        import httpx
        order={'orderNo':'SO123-abc','status':'PAID_PENDING_SHIPMENT','fulfillmentStatus':'UNSHIPPED','totalAmount':99,'itemSummary':['耳机']}
        req=self.request([order]);plan=QueryPlan(normalized_question='查单号',target='orders',scope='specific',order_ids=['SO123-abc'],fields=['tracking'])
        response=httpx.Response(404,request=httpx.Request('GET','http://local/logistics'))
        with patch('tools.read_queries.ecommerce_get',side_effect=httpx.HTTPStatusError('missing logistics',request=response.request,response=response)):
            answer,calls,_=detail_answer(req,'SO123-abc',plan=plan)
        self.assertIn('订单存在',answer);self.assertNotIn('未查询到该订单',answer)
    def test_router_extra_plan_is_separate_and_route_remains_strict(self):
        import json
        data=dict(intent='order_query',needs_rag=False,needs_business_tools=True,required_tools=['get_order_detail'],knowledge_domains=[],risk_level='low',requires_workflow=False,fallback_policy='tool_first',query_plan={'target':'orders'})
        self.assertIsNotNone(RouteModelClient._extract_candidate(json.dumps(data)))
        data['random_untrusted_field']='oops'
        self.assertIsNone(RouteModelClient._extract_candidate(json.dumps(data)))

if __name__=='__main__':unittest.main()
