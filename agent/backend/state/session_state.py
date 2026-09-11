"""课程级内存状态。这里模拟会话、反馈、缓存、checkpoint 和幂等记录。

课程边界：这些全局对象用于本地快照观察，不是生产级持久化存储。
真实系统应把会话、反馈、缓存、checkpoint 和幂等记录放进数据库、
Redis、队列或审计系统，并处理过期、并发、权限和清理策略。
"""

from __future__ import annotations

from typing import Any

from api.schemas import FeedbackRecord

MESSAGE_COUNT_BY_SESSION: dict[str, int] = {}
FEEDBACK_RECORDS: list[FeedbackRecord] = []
BACKFILLED_CASES: list[dict[str, Any]] = []
COMMON_HIT_CACHE: dict[str, dict[str, Any]] = {}
WORKFLOW_CHECKPOINTS: dict[tuple[str, str], dict[str, Any]] = {}
SUBMITTED_ACTIONS: dict[str, dict[str, Any]] = {}
