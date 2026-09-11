"""电商业务后端集成层。课程代码通过这里获取实时订单事实。"""

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

from config.settings import ecommerce_base_url, load_course_env

COURSE_SEED_ORDER_MIRRORS: dict[str, dict[str, Any]] = {
    "SO20260601090000008-a1000008": {
        "orderNo": "SO20260601090000008-a1000008",
        "userId": "U1001",
        "paymentStatus": "PAID",
        "fulfillmentStatus": "PAID_PENDING_SHIPMENT",
        "items": [{"productName": "降噪蓝牙耳机"}],
    },
    "SO20260602103000009-a1000009": {
        "orderNo": "SO20260602103000009-a1000009",
        "userId": "U1001",
        "paymentStatus": "PAID",
        "fulfillmentStatus": "SHIPPED",
        "logisticsStatus": "IN_TRANSIT",
        "items": [{"productName": "65W GaN 快充充电器"}],
    },
    "SO20260712090000010-a1000010": {
        "orderNo": "SO20260712090000010-a1000010",
        "userId": "U1001",
        "paymentStatus": "PAID",
        "fulfillmentStatus": "DELIVERED",
        "logisticsStatus": "SIGNED",
        "deliveredAt": "2026-07-12T09:00:00",
        "returnable": True,
        "items": [{"productName": "降噪蓝牙耳机", "returnable": True}],
    },
}

COURSE_SEED_PRODUCT_MIRRORS: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "降噪蓝牙耳机",
        "code": "SKU-AUD-101",
        "category": "消费电子",
        "price": 599.0,
        "stock": 520,
        "active": True,
        "returnable": True,
        "highlights": "通勤首选；支持快充；参加会员满减活动",
        "promotion": {
            "promotionName": "消费电子活动会场",
            "promotionType": "member_discount",
            "discountSummary": "耳机、音箱和快充配件进入 618 消费电子会场，活动价和会员条件以结算页为准。",
            "promotionPrice": 529.0,
            "requiredMemberLevel": "gold",
            "conditionSummary": "金卡会员专享",
        },
    }
]

COURSE_SEED_AFTER_SALE_MIRRORS: dict[str, list[dict[str, Any]]] = {
    "SO20260602103000009-a1000009": [
        {
            "requestId": "AS-STORY-REFUND-0009",
            "orderNo": "SO20260602103000009-a1000009",
            "userId": "U1001",
            "requestType": "REFUND",
            "status": "REVIEWING",
        }
    ]
}


def course_seed_mirror_enabled() -> bool:
    """业务种子镜像只供显式离线课程测试使用，不能掩盖在线接口故障。"""
    return os.getenv("AGENT_COURSE_OFFLINE_FACTS") == "1"


def _with_fact_source(value: dict[str, Any], source: str) -> dict[str, Any]:
    return {**value, "_fact_source": source}

def delegated_service_headers(current_user_id: str | None) -> dict[str, str]:
    """总演习只用业务事实中的当前用户构造已认证 Agent 服务身份。"""
    load_course_env()
    user_id = str(current_user_id or "").strip()
    token = os.getenv(
        "AGENT_ECOMMERCE_SERVICE_TOKEN",
        os.getenv("AGENT_SERVICE_AUTH_TOKEN", ""),
    ).strip()
    if not user_id or not token:
        return {}
    return {"X-Agent-Service-Token": token, "X-Agent-User-Id": user_id}

def ecommerce_get(
    path: str,
    *,
    delegated_user_id: str | None = None,
) -> dict[str, Any] | list[Any] | None:
    """封装业务后端 GET 调用，统一处理响应结构和错误边界。"""
    # 课程业务后端通常运行在 localhost；不继承宿主机 HTTP 代理，避免本地请求被代理劫持。
    with httpx.Client(timeout=5, trust_env=False) as client:
        response = client.get(
            f"{ecommerce_base_url()}{path}",
            headers=delegated_service_headers(delegated_user_id),
        )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return None
    return payload.get("data")

def order_fact_from_ecommerce(target_order_no: str, current_user_id: str) -> dict[str, Any] | None:
    """从业务后端读取订单事实；失败时返回空值，交给 Agent 降级或转人工。"""
    try:
        order = ecommerce_get(f"/api/orders/{target_order_no}", delegated_user_id=current_user_id)
    except Exception:
        if not course_seed_mirror_enabled():
            raise
        order = None
    if isinstance(order, dict):
        enriched = _with_fact_source(order, "business_api")
        items = enriched.get("items") or []
        product_facts: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict) or item.get("productId") is None:
                product_facts.append(item)
                continue
            try:
                product = ecommerce_get(f"/api/products/{item['productId']}")
            except Exception:
                product = None
            product_facts.append({**item, "returnable": product.get("returnable")} if isinstance(product, dict) else item)
        if product_facts:
            enriched["items"] = product_facts
            returnability = [item.get("returnable") for item in product_facts if isinstance(item, dict)]
            if returnability and all(value is True for value in returnability):
                enriched["returnable"] = True
            elif any(value is False for value in returnability):
                enriched["returnable"] = False
            else:
                enriched["returnable"] = None
        return enriched
    if not course_seed_mirror_enabled():
        return None
    mirror = COURSE_SEED_ORDER_MIRRORS.get(target_order_no)
    return _with_fact_source(mirror, "course_seed_mirror") if mirror else None


def products_from_ecommerce(keyword: str) -> list[dict[str, Any]]:
    """查询实时商品事实；课程离线演练只回退到固定、可识别的商品样例。"""
    try:
        query_keyword = product_query_keyword(keyword)
        products = ecommerce_get(f"/api/products?{httpx.QueryParams({'keyword': query_keyword})}")
    except Exception:
        products = None
    if isinstance(products, list):
        return [_with_fact_source(item, "business_api") for item in products if isinstance(item, dict)]
    if not course_seed_mirror_enabled():
        return []
    normalized = keyword.replace(" ", "")
    return [
        _with_fact_source(item, "course_seed_mirror")
        for item in COURSE_SEED_PRODUCT_MIRRORS
        if any(term in normalized for term in ("耳机", "降噪", "通勤")) and "耳机" in str(item.get("name"))
    ]


def product_query_keyword(user_message: str) -> str:
    """把自然语言商品咨询收窄成业务后端可搜索的关键词。"""
    for term in ("降噪蓝牙耳机", "降噪耳机", "耳机", "音箱", "充电器", "投影仪", "键盘"):
        if term in user_message:
            return "降噪" if term in {"降噪蓝牙耳机", "降噪耳机"} else term
    return user_message.strip()


def after_sale_requests_from_ecommerce(order_id: str, current_user_id: str) -> list[dict[str, Any]] | None:
    """按订单号读取售后进度；None 表示业务接口不可用，空列表表示确认没有记录。"""
    try:
        order = order_fact_from_ecommerce(order_id, current_user_id)
        if not current_user_id:
            raise ValueError("missing_current_user_id")
        requests = ecommerce_get(
            f"/api/after-sale/requests?orderNo={order_id}",
            delegated_user_id=current_user_id,
        )
    except Exception:
        requests = None
    if isinstance(requests, list):
        return [_with_fact_source(item, "business_api") for item in requests if isinstance(item, dict)]
    if not course_seed_mirror_enabled():
        return None
    return [_with_fact_source(item, "course_seed_mirror") for item in COURSE_SEED_AFTER_SALE_MIRRORS.get(order_id, [])]
