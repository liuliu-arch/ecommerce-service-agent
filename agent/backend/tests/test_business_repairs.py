import unittest,os
from datetime import date
from unittest.mock import patch
import httpx
from fastapi import HTTPException
from api.schemas import ChatRequest,HistoryMessage
from api.session_access import SessionAccess
from context.builder import build_context,SESSION_MEMORIES
from tools.read_queries import select_products,list_orders,product_answer,knowledge_question,error_call,boundary_kind
from workflows.after_sale_graph import course_today

def request(q,ctx=None):return ChatRequest(session_id='repair-unit',runtime_user_id='alice',user_message=q,runtime_context=ctx)

class BusinessRepairTests(unittest.TestCase):
    def test_capability_cannot_be_guessed_or_shared_across_users(self):
        access=SessionAccess();token=access.chat('s','alice',None)
        access.require('s','alice',token)
        for user,tok in [('alice',None),('alice','wrong'),('bob',token)]:
            with self.assertRaises(HTTPException):access.require('s',user,tok)
        with self.assertRaises(HTTPException):access.chat('s','bob',token)
        with self.assertRaises(HTTPException):access.chat('existing-eval-session','alice',None,existing_trace=True)

    def test_address_edit_is_not_refund_or_knowledge_query(self):
        self.assertEqual(boundary_kind('把收货地址改成新的地址'),'address')
        self.assertEqual(boundary_kind('帮我修改收货地址'),'address')

    def test_real_clock_and_explicit_fixture_clock(self):
        with patch.dict(os.environ,{},clear=True):self.assertEqual(course_today(),date.today())
        with patch.dict(os.environ,{'AGENT_COURSE_TODAY':'2025-02-01'}):self.assertEqual(course_today(),date(2025,2,1))

    def test_exact_product_not_first_category_result(self):
        products=[{'name':'专业降噪蓝牙耳机'},{'name':'轻量蓝牙耳机'}]
        self.assertEqual(select_products('轻量蓝牙耳机多少钱？',products),[products[1]])
        self.assertEqual(select_products('不存在的火星耳机多少钱？',products),[])
        self.assertEqual(select_products('专业降噪蓝牙耳机和轻量蓝牙耳机对比',products),products)

    def test_budget_and_stock_joint_filter(self):
        products=[{'name':'甲款耳机','price':100,'stock':0,'active':True},{'name':'乙款耳机','price':400,'stock':4,'active':True},{'name':'丙款耳机','price':200,'stock':2,'active':True}]
        with patch('tools.read_queries.ecommerce_get',return_value=products):
            answer,call,_=product_answer(request('预算300元以内推荐有现货的耳机'))
        self.assertEqual(call.arguments['product_names'],['丙款耳机'])
        self.assertIn('200',answer)

    def test_list_month_total_and_foreign_filter(self):
        orders=[{'orderNo':'a','userId':'alice','createdAt':'2025-05-01','totalAmount':10.1,'items':[]}, {'orderNo':'b','createdAt':'2025-05-02','totalAmount':20.2,'items':[]},{'orderNo':'c','userId':'bob','createdAt':'2025-05-02','totalAmount':100,'items':[]}]
        answer,call=list_orders(request('2025年5月订单一共多少钱',{'currentUserOrders':orders,'currentUserOrdersTruncated':False}))
        self.assertIn('30.3',answer);self.assertEqual(call.arguments['count'],2)
        self.assertIn('未扣除退款',answer)

    def test_empty_complete_is_not_missing_context(self):
        with patch('tools.read_queries.ecommerce_get') as fetch:
            answer,_=list_orders(request('所有订单',{'currentUserOrders':[],'currentUserOrdersTruncated':False}))
            fetch.assert_not_called();self.assertIn('没有',answer)

    def test_truncated_snapshot_refetches_and_does_not_claim_total(self):
        with patch('tools.read_queries.ecommerce_get',return_value={'orders':[],'truncated':True}) as fetch:
            answer,_=list_orders(request('所有订单一共多少钱',{'currentUserOrders':[],'currentUserOrdersTruncated':True}))
            fetch.assert_called_once();self.assertIn('暂不能准确计算',answer)

    def test_error_classes_are_distinct(self):
        unavailable=error_call('x',{},httpx.ConnectError('offline'))
        missing=error_call('x',{},httpx.HTTPStatusError('404',request=httpx.Request('GET','http://local'),response=httpx.Response(404)))
        self.assertEqual(unavailable.error_type,'business_api_unavailable');self.assertEqual(missing.error_type,'not_found')

    def test_history_entity_only_is_recovered_then_verified_by_tool(self):
        SESSION_MEMORIES.clear();r=request('刚才那个订单发货了吗？')
        r.history_messages=[HistoryMessage(role='user',content='订单SO20250101090000001-abcdef12')]+[HistoryMessage(role='assistant',content='无关内容'*100)]*12
        chosen,_,_=build_context(r,None)
        self.assertEqual(chosen,'SO20250101090000001-abcdef12')

    def test_mixed_query_preserves_only_knowledge_clause(self):
        self.assertEqual(knowledge_question('商品多少钱？另外发票在哪里下载？'),'发票在哪里下载')

if __name__=='__main__':unittest.main()
