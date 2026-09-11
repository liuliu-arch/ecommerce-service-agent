"""Read-only business queries: preserve entities, fields and user-scoped facts."""
from __future__ import annotations

import re
from decimal import Decimal
from urllib.parse import quote

import httpx
from api.schemas import ToolCallTrace
from integrations.ecommerce_client import ecommerce_get
from tools.runtime_context import item_names, order_no, order_status_label, logistics_status_label
from tools.tool_runtime import get_order_detail, get_order_logistics


def boundary_kind(text):
    if re.search(r'(系统提示词|API.?密钥|忽略.*规则|hidden reasoning)', text, re.I):
        return None
    if re.search(r'(找|转|联系|接|要).*人工', text) and not re.search(r'(订单|退款|退货|政策|发票|券)', text):
        return 'human'
    if re.search(r'(修改|改成|更改|改一下|改).*地址|地址.*(修改|更改|改成|改一下)', text):
        return 'address'
    if re.search(r'重复扣款|扣了两次|多扣|扣重', text):
        return 'payment_dispute'
    if re.search(r'(直接取消|取消订单|取消.*SO)', text):
        return 'cancel'
    if re.search(r'账户余额|账号余额|可用优惠券|有几张.*券', text):
        return 'account'
    if re.search(r'(我|当前).*(会员等级|什么会员|哪个等级)', text):
        return 'identity'
    if re.search(r'退货|退款', text) and not re.search(r'SO\d|我想退|我要退|帮我退|申请退', text) and re.search(r'运费|一般|政策|规则|条件|流程', text):
        return 'policy'
    return None


def knowledge_question(text):
    """Only the policy clauses; business facts must not be looked up in RAG."""
    clauses = re.split(r'[？?；;。！!]|另外[，,]?|此外[，,]?', text)
    chosen=[]
    for clause in clauses:
        if re.search(r'发票|抬头|满减|满\s*\d+\s*减|叠加|会员券|运费', clause):
            # Split a business clause joined with a policy clause by a comma.
            parts=re.split(r'[，,]',clause)
            chosen.extend(p.strip() for p in parts if re.search(r'发票|抬头|满减|满\s*\d+\s*减|叠加|会员券|运费',p))
    return '；'.join(chosen)


def is_collection_query(text):
    return bool(re.search(r'所有|全部|有哪些|都列|一共|总共|合计|最近|最新|\d{1,2}\s*月|待发货.*订单|订单.*待发货|买过|买的.*订单',text))


def error_call(name, arguments, exc):
    status=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else None
    error='owner_mismatch' if status in (401,403) else 'not_found' if status==404 else 'business_api_unavailable'
    answer={'owner_mismatch':'当前用户无权查询该订单或账户，不能提供相关详情。',
            'not_found':'未查询到该订单或商品，请核对信息。',
            'business_api_unavailable':'业务服务暂时不可用，无法核实最新数据，请稍后重试或转人工客服。'}[error]
    return ToolCallTrace(tool_name=name,arguments=arguments,output_summary=answer,status='error',error_type=error,risk_level='medium',next_action='transfer_to_human')


def money(value):
    return format(Decimal(str(value)), 'f').rstrip('0').rstrip('.') if '.' in str(value) else str(value)


def order_line(order):
    fields=[f"订单 {order_no(order)}",'商品：'+'、'.join(item_names(order)), '状态：'+order_status_label(order)]
    if order.get('totalAmount') is not None:fields.append('订单金额：'+money(order['totalAmount'])+' 元')
    if order.get('createdAt'):fields.append('下单时间：'+str(order['createdAt']))
    return '；'.join(fields)+'。'


def list_orders(request, plan=None):
    page=request.runtime_context or {};source='runtime_context'
    try:
        orders=page.get('currentUserOrders')
        truncated=page.get('currentUserOrdersTruncated',True)
        if not isinstance(orders,list) or truncated:
            data=ecommerce_get('/api/course-debug/users/'+quote(request.runtime_user_id,safe='')+'/order-context?limit=50',delegated_user_id=request.runtime_user_id)
            if not isinstance(data,dict):raise ValueError('invalid_order_context')
            orders=data['orders'];truncated=data['truncated'];source='business_api'
        # Missing userId is valid in the user-scoped summary DTO; explicit foreign IDs are never accepted.
        orders=[o for o in orders if isinstance(o,dict) and (o.get('userId') or o.get('user_id') or request.runtime_user_id)==request.runtime_user_id]
        query=request.user_message
        if plan is None:
            query=request.user_message
            if re.search('待发货|未发货',query):orders=[o for o in orders if order_status_label(o)=='待发货']
            elif re.search('已签收|已送达',query):orders=[o for o in orders if order_status_label(o) in ('已送达','已签收')]
            elif '已发货' in query:orders=[o for o in orders if order_status_label(o)=='已发货']
            month=re.search(r'(?:(\d{4})年)?\s*(\d{1,2})\s*月',query)
            if month:
                orders=[o for o in orders if len(str(o.get('createdAt','')))>=7 and int(str(o['createdAt'])[5:7])==int(month[2]) and (not month[1] or str(o['createdAt']).startswith(month[1]))]
            for category in ('耳机','充电器','键盘','音箱','手机','相机','平板'):
                if category in query:orders=[o for o in orders if any(category in name for name in item_names(o))]
            orders=sorted(orders,key=lambda o:str(o.get('createdAt','')),reverse=True)
            if re.search('最近|最新',query):orders=orders[:1]
        else:
            statuses={'待发货':'UNSHIPPED','已发货':'SHIPPED','已送达':'DELIVERED','已签收':'DELIVERED'}
            if plan.order_ids:orders=[o for o in orders if order_no(o) in plan.order_ids]
            if plan.statuses:orders=[o for o in orders if statuses.get(order_status_label(o)) in plan.statuses]
            if plan.date_from:orders=[o for o in orders if str(o.get('createdAt',''))[:10]>=plan.date_from.isoformat()]
            if plan.date_to:orders=[o for o in orders if str(o.get('createdAt',''))[:10]<=plan.date_to.isoformat()]
            if plan.product_terms:orders=[o for o in orders if any(normalize(t) in normalize(n) for t in plan.product_terms for n in item_names(o))]
            def in_amount(o):
                if o.get('totalAmount') is None:return plan.amount_min is None and plan.amount_max is None
                value=Decimal(str(o['totalAmount']))
                return (plan.amount_min is None or (value>=plan.amount_min if plan.min_inclusive else value>plan.amount_min)) and (plan.amount_max is None or (value<=plan.amount_max if plan.max_inclusive else value<plan.amount_max))
            orders=[o for o in orders if in_amount(o)]
            orders=sorted(orders,key=lambda o:str(o.get('createdAt','')),reverse=True)
            if plan.scope=='latest':orders=orders[:1]
        if truncated:
            prefix='目前仅加载部分订单，以下不是全部订单，完整列表请在商城“我的订单”查看。'
        else:prefix=f'查询到 {len(orders)} 笔符合条件的订单。' if orders else '当前没有符合条件的订单。'
        if ('sum' in plan.operations) if plan else re.search('一共|总共|合计|总金额',query):
            if truncated:answer=prefix+'数据不完整，暂不能准确计算全部订单金额。'
            elif any(o.get('totalAmount') is None for o in orders):answer=prefix+'部分订单缺少金额，暂不能准确计算合计。'
            else:answer=prefix+f"订单金额合计 {money(sum((Decimal(str(o['totalAmount'])) for o in orders),Decimal('0')))} 元；这是订单金额合计，未扣除退款，不代表净实付金额。"
        else:answer=prefix+('\n'+'\n'.join(order_line(o) for o in orders) if orders else '')
        if plan and 'sum' in plan.operations and 'list' in plan.operations and orders:
            answer += '\n'+'\n'.join(order_line(o) for o in orders)
        return answer,ToolCallTrace(tool_name='list_user_orders',arguments={'fact_source':source,'count':len(orders),'truncated':truncated,'query_plan':plan.model_dump(mode='json') if plan else None},output_summary=answer,status='success',risk_level='low',next_action='answer_user')
    except Exception as exc:
        call=error_call('list_user_orders',{},exc);return call.output_summary,call


def detail_answer(request,order_id,before=lambda name,args:None,plan=None):
    before('get_order_detail',{'order_id':order_id})
    order,call=get_order_detail(order_id,request.runtime_user_id,request.runtime_context)
    calls=[call]
    if order is None:return call.output_summary,calls,None
    answer=order_line(order)
    query=request.user_message
    if (plan and set(plan.fields)&{'logistics','tracking','shipping_time','delivery_time'}) or re.search('物流|快递|发货|送到|到哪|到了|送达|单号',query):
        before('get_order_logistics',{'order_id':order_id})
        logistics=get_order_logistics(order);calls.append(logistics);answer+=' '+logistics.output_summary
    if (plan and 'tracking' in plan.fields) or re.search('物流单号|快递单号|运单|物流节点',query):
        try:
            before('get_order_logistics',{'order_id':order_id,'fact_source':'business_api'})
            data=ecommerce_get('/api/orders/'+quote(order_id,safe='')+'/logistics',delegated_user_id=request.runtime_user_id)
            if not isinstance(data,dict):raise ValueError('invalid_logistics')
            tracking=data.get('logisticsNo') or data.get('trackingNo') or order.get('logisticsNo')
            extra='物流单号：'+str(tracking)+'。' if tracking else '当前物流数据未提供运单号，请稍后刷新订单详情或联系人工核实。'
            calls.append(ToolCallTrace(tool_name='get_order_logistics',arguments={'order_id':order_id,'fact_source':'business_api'},output_summary=extra,status='success',risk_level='low'))
            answer+=' '+extra
        except Exception as exc:
            if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code==404:
                extra='订单存在，但当前没有物流记录，尚未发货时暂无快递单号。' if order_status_label(order)=='待发货' else '订单存在，但当前没有查到对应物流记录，请联系商家或承运商核实。'
                calls.append(ToolCallTrace(tool_name='get_order_logistics',arguments={'order_id':order_id},output_summary=extra,status='success',risk_level='low'))
                answer+=' '+extra
            else:
                failure=error_call('get_order_logistics',{'order_id':order_id},exc);calls.append(failure);answer+=' '+failure.output_summary
    if re.search('明天|一定|几点|什么时候到|预计|多久.*到|保证',query):answer+=' 当前数据不能确认具体送达时间，无法保证按指定时间送达；请查看承运商最新物流或联系人工核实。'
    if plan and 'shipping_time' in plan.fields:
        answer += (' 发货时间：'+str(order['shippedAt'])+'。') if order.get('shippedAt') else ' 当前数据未提供预计发货时间，无法确认何时寄出，请联系商家核实。'
    if plan and 'delivery_time' in plan.fields:answer += ' 当前数据不能保证具体送达时间，请查看承运商最新物流。'
    if plan and 'recipient' in plan.fields:answer += ' 当前数据无法确认实际签收人；若显示签收但没有收到，请联系承运商或商家人工客服核验签收凭证和包裹去向。'
    # Complete typed evidence is also the fallback; it must preserve every requested field.
    call.output_summary=answer
    return answer,calls,order_no(order)


def normalize(text):
    return re.sub(r'\W+','',str(text)).lower()


def select_products(query,catalog):
    q=normalize(query)
    exact=[]
    for p in catalog:
        name=normalize(p.get('name',''))
        aliases={name,name.replace('蓝牙',''),name.replace('5g','')}
        if any(a and a in q for a in aliases):exact.append(p)
    if exact:return exact
    # Generic category search is distinct from an unrecognized named product.
    for category in ('耳机','充电器','音箱','手机','平板','键盘','相机','空调','手表','显示器'):
        if category not in query:continue
        prefix=query.split(category)[0]
        generic=not prefix.strip() or bool(re.search(r'推荐|预算|以内|以下|什么|有没有|有现货|买个|买一|想买',prefix))
        if generic:return [p for p in catalog if category in p.get('name','')]
        return []
    return []


def product_answer(request, plan=None):
    query=request.user_message
    try:
        catalog=ecommerce_get('/api/products')
        if not isinstance(catalog,list):raise ValueError('invalid_product_catalog')
        if plan:
            products, ambiguous = resolve_products(plan.product_terms,catalog)
            if ambiguous:
                answer='商品名称无法唯一确定，请确认具体型号：'+'、'.join(ambiguous)+'。'
                return answer,ToolCallTrace(tool_name='search_products',arguments={'terms':plan.product_terms,'candidates':ambiguous},output_summary=answer,status='success',risk_level='low',next_action='ask_clarification'),None
        else:products=select_products(query,catalog)
        budget=re.search(r'(?:预算\s*)?(\d+(?:\.\d+)?)\s*元?\s*(?:以内|以下)',query)
        if plan:budget=None
        if budget:products=[p for p in products if p.get('price') is not None and Decimal(str(p['price']))<=Decimal(budget[1])]
        if plan:
            if plan.amount_max is not None:products=[p for p in products if p.get('price') is not None and (Decimal(str(p['price']))<=plan.amount_max if plan.max_inclusive else Decimal(str(p['price']))<plan.amount_max)]
            if plan.amount_min is not None:products=[p for p in products if p.get('price') is not None and (Decimal(str(p['price']))>=plan.amount_min if plan.min_inclusive else Decimal(str(p['price']))>plan.amount_min)]
        if (plan.in_stock if plan else re.search('推荐|有现货',query)):products=[p for p in products if p.get('active') is True and (p.get('stock') or 0)>0]
        if not products:
            answer='未查询到符合商品名称'+('、预算和现货条件' if budget or '推荐' in query else '')+'的商品；请核对商品名称或调整条件。'
            return answer,ToolCallTrace(tool_name='search_products',arguments={'query':query,'fact_source':'business_api','matched_count':0},output_summary=answer,status='success',risk_level='low',next_action='ask_clarification'),None
        lines=[]
        for p in products:
            parts=[p['name']]
            if p.get('price') is not None:parts.append(f"标价 {money(p['price'])} 元")
            if p.get('stock') is not None:parts.append(f"库存 {p['stock']} 件"+('，当前缺货' if p['stock']==0 else ''))
            if p.get('active') is False:parts.append('商品已下架，当前不能购买，有库存不代表可销售')
            promotion=p.get('promotion') or {}
            if promotion.get('promotionPrice') is not None:
                parts.append(f"活动价 {money(promotion['promotionPrice'])} 元，{promotion.get('conditionSummary') or '适用条件以结算页为准'}")
                if promotion.get('requiredMemberLevel') and promotion['requiredMemberLevel']!=request.runtime_member_level:parts.append('你当前的会员等级不满足此专享价条件，不能按该价格承诺成交')
            if p.get('description'):parts.append(p['description'])
            if p.get('afterSaleLimit'):parts.append('商品售后限制：'+p['afterSaleLimit'])
            lines.append('；'.join(parts)+'。')
        answer='\n'.join(lines)
        if plan and 'compare' in plan.operations and len(products)>1 and all(p.get('price') is not None for p in products):
            lowest=min(Decimal(str(p['price'])) for p in products)
            cheapest=[p['name'] for p in products if Decimal(str(p['price']))==lowest]
            answer+='\n标价最低的是：'+'、'.join(cheapest)+'，'+money(lowest)+'元；能否购买请同时看上面的库存和上架状态。'
        call=ToolCallTrace(tool_name='search_products',arguments={'query':query,'query_plan':plan.model_dump(mode='json') if plan else None,'product_names':[p['name'] for p in products],'fact_source':'business_api','matched_count':len(products)},output_summary=answer,status='success',risk_level='low',next_action='answer_user')
        return answer,call,products[0]['name'] if len(products)==1 else None
    except Exception as exc:
        call=error_call('search_products',{'query':query},exc);return call.output_summary,call,None


BOUNDARY_ANSWERS={
 'human':'当前调试台没有真人客服接入功能。我可以标记需要人工处理，但不能为你接通真人坐席；请通过实际商家的客服渠道联系工作人员。',
 'address':'我目前不能直接修改收货地址。请在商城订单详情确认是否支持修改；已发货订单请联系人工或承运商核实，地址尚未修改。',
 'cancel':'我目前不能直接取消订单。请在订单详情查看可用操作；已发货订单需要人工核实拦截或售后方式，当前未取消订单。',
 'payment_dispute':'请提供订单号，并在支付平台核对两笔扣款记录和支付状态；不要发送密码或完整银行卡号。若确认重复扣款，请通过订单详情联系客服核实。我暂未认定发生重复扣款，也未发起退款。',
 'account':'当前助手尚未接入账户余额和个人优惠券查询工具，无法核实具体金额或张数。请在商城“我的”页面查看余额及优惠券，或使用商城的客服入口核实。',
}


def resolve_products(terms,catalog):
    """Resolve terms against real catalog names; never invent a product or silently choose a close tie."""
    from difflib import SequenceMatcher
    selected=[]
    ambiguous=[]
    categories={'耳机','充电器','音箱','手机','平板','键盘','相机','空调','手表','显示器'}
    def key(text):
        return normalize(text).replace('氮化镓','gan').replace('瓦','w').replace('充电头','充电器').replace('降躁','降噪')
    for term in terms:
        q=key(term)
        exact=[p for p in catalog if q==key(p['name'])]
        if not exact:exact=[p for p in catalog if q and q in key(p['name'])]
        if exact:
            if len(exact)>1 and term not in categories:
                ambiguous.extend(p['name'] for p in exact)
            else:selected.extend(exact)
            continue
        ranked=sorted(((SequenceMatcher(None,q,key(p['name'])).ratio(),p) for p in catalog),key=lambda x:x[0],reverse=True)
        if ranked and ranked[0][0]>=0.62:
            close=[p for score,p in ranked if score>=ranked[0][0]-0.12]
            if len(close)>1:ambiguous.extend(p['name'] for p in close)
            else:selected.append(ranked[0][1])
    return list({p['name']:p for p in selected}.values()),list(dict.fromkeys(ambiguous))
