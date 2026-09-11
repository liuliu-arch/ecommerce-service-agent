"""业务工具执行层。这里封装订单详情和物流查询，并返回可观察 ToolCallTrace。"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import httpx
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.schemas import *
from integrations.ecommerce_client import after_sale_requests_from_ecommerce, order_fact_from_ecommerce, products_from_ecommerce
from tools.runtime_context import *

def get_order_detail(
    order_id: str | None,
    runtime_user_id: str,
    runtime_context: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, ToolCallTrace]:
    """执行订单详情工具，同时校验订单归属，防止越权售后操作。"""
    arguments = {"order_id": order_id}
    if order_id is None:
        return None, ToolCallTrace(
            tool_name="get_order_detail",
            arguments=arguments,
            output_summary="缺少订单号，不能查询订单。",
            status="error",
            error_type="missing_order_id",
            next_action="ask_clarification",
        )
    try:
        order = find_context_order(runtime_context, order_id) or order_fact_from_ecommerce(order_id, runtime_user_id)
    except Exception as exc:
        from tools.read_queries import error_call
        return None, error_call("get_order_detail", arguments, exc)
    if order is None:
        return None, ToolCallTrace(
            tool_name="get_order_detail",
            arguments=arguments,
            output_summary=f"订单 {order_id} 不存在或当前业务系统暂未返回该订单。",
            status="error",
            error_type="not_found",
            risk_level="medium",
            next_action="ask_clarification",
        )
    if order_user_id(order) and order_user_id(order) != runtime_user_id:
        return None, ToolCallTrace(
            tool_name="get_order_detail",
            arguments=arguments,
            output_summary=f"订单 {order_id} 没有通过当前用户归属校验。",
            status="error",
            error_type="owner_mismatch",
            risk_level="medium",
            next_action="transfer_to_human",
        )
    arguments["fact_source"] = order.get("_fact_source", "runtime_context")
    summary = f"订单 {order_no(order)} 当前状态为{order_status_label(order)}，物流状态为{logistics_status_label(order)}，商品 {'、'.join(item_names(order))}。"
    if order.get("totalAmount") is not None:
        summary += f" 订单金额 {order['totalAmount']} 元。"
    return order, ToolCallTrace(tool_name="get_order_detail", arguments=arguments, output_summary=summary, status="success", risk_level="low")


def get_order_logistics(order: dict[str, Any]) -> ToolCallTrace:
    """基于订单事实生成物流工具结果，不让模型凭空猜测实时状态。"""
    return ToolCallTrace(
        tool_name="get_order_logistics",
        arguments={"order_id": order_no(order)},
        output_summary=f"物流状态为{logistics_status_label(order)}，订单状态为{order_status_label(order)}。",
        status="success",
        risk_level="low",
        next_action="answer_user",
    )


def get_refund_status(order: dict[str, Any], runtime_user_id: str) -> ToolCallTrace:
    """读取已存在的售后申请状态；查询进度绝不能隐式创建新退款。"""
    requests = after_sale_requests_from_ecommerce(order_no(order), runtime_user_id)
    if requests is None:
        return ToolCallTrace(
            tool_name="get_refund_status",
            arguments={"order_id": order_no(order), "fact_source": "business_api_unavailable"},
            output_summary=f"订单 {order_no(order)} 的退款进度暂时无法从业务系统核实，本轮不会猜测退款状态，建议稍后重试或转人工客服。",
            status="error",
            risk_level="medium",
            next_action="transfer_to_human",
            error_type="business_api_unavailable",
        )
    refund_requests = [item for item in requests if str(item.get("requestType") or item.get("type") or "").upper() in {"REFUND", "CANCEL_ORDER"}]
    if not refund_requests:
        return ToolCallTrace(
            tool_name="get_refund_status",
            arguments={"order_id": order_no(order), "fact_source": order.get("_fact_source", "runtime_context")},
            output_summary=f"订单 {order_no(order)} 暂未查询到退款申请记录。",
            status="success",
            risk_level="low",
            next_action="answer_user",
        )
    latest = max(
        refund_requests,
        key=lambda item: str(item.get("updatedAt") or item.get("createdAt") or ""),
    )
    request_id = str(latest.get("requestId") or latest.get("requestNo") or "未知申请号")
    status = str(latest.get("status") or "UNKNOWN").upper()
    status_label = {"PENDING": "待处理", "REVIEWING": "审核中", "APPROVED": "已通过", "REJECTED": "未通过", "COMPLETED": "已完成"}.get(status, status)
    return ToolCallTrace(
        tool_name="get_refund_status",
        arguments={"order_id": order_no(order), "fact_source": latest.get("_fact_source", "business_api")},
        output_summary=f"退款申请 {request_id} 当前状态为{status_label}。",
        status="success",
        risk_level="low",
        next_action="answer_user",
    )


def search_products(keyword: str) -> tuple[list[dict[str, Any]], ToolCallTrace]:
    """查询商品实时价格、库存和活动事实；稳定叠加规则仍由 RAG 提供。"""
    products = products_from_ecommerce(keyword)
    if not products:
        return [], ToolCallTrace(
            tool_name="search_products",
            arguments={"keyword": keyword, "fact_source": "business_api_unavailable"},
            output_summary="没有查询到匹配商品，不能猜测库存或价格。",
            status="error",
            risk_level="low",
            next_action="ask_clarification",
            error_type="product_not_found",
        )
    product = products[0]
    name = str(product.get("name") or product.get("productName") or "商品")
    stock = product.get("stock")
    price = product.get("price")
    summary = f"{name} 商品标价 {price} 元，库存 {stock} 件。"
    promotion = product.get("promotion")
    if isinstance(promotion, dict):
        promotion_name = promotion.get("promotionName")
        promotion_price = promotion.get("promotionPrice")
        condition = promotion.get("conditionSummary")
        discount_summary = promotion.get("discountSummary")
        promotion_facts = [
            f"当前活动为{promotion_name}" if promotion_name else None,
            f"活动价 {promotion_price} 元" if promotion_price is not None else None,
            f"适用条件为{condition}" if condition else None,
            str(discount_summary).rstrip("。") if discount_summary else None,
        ]
        facts = "，".join(fact for fact in promotion_facts if fact)
        if facts:
            summary += f" {facts}。"
    return products, ToolCallTrace(
        tool_name="search_products",
        arguments={
            "keyword": keyword,
            "product_name": name,
            "fact_source": product.get("_fact_source", "business_api"),
        },
        output_summary=summary,
        status="success",
        risk_level="low",
        next_action="answer_user",
    )
