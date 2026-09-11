"""按来源标记上下文污染，避免不可信文本伪装成系统指令。"""

from __future__ import annotations

import re
from typing import Any


_INJECTION_PATTERNS = (
    re.compile(r"忽略(?:之前|以上|所有).{0,12}(?:指令|规则|提示词)", re.IGNORECASE),
    re.compile(r"(?:system|developer)\s*(?:message|prompt|指令)", re.IGNORECASE),
    re.compile(r"你现在(?:必须|是|扮演)|改写系统提示词", re.IGNORECASE),
    re.compile(r"输出(?:隐藏|内部|完整).{0,8}(?:推理|提示词|策略)", re.IGNORECASE),
)


def inspect_source(source: str, content: str) -> dict[str, Any]:
    """返回公开安全摘要；不把命中的攻击原文写入 Trace。"""
    categories = ["instruction_override"] if any(pattern.search(content) for pattern in _INJECTION_PATTERNS) else []
    return {
        "source": source,
        "tainted": bool(categories),
        "categories": categories,
        "sanitized_content": "[tainted-source-redacted]" if categories else content,
    }


def inspect_sources(items: list[tuple[str, str]]) -> tuple[list[str], list[dict[str, Any]]]:
    reports = [inspect_source(source, content) for source, content in items]
    return [str(report["sanitized_content"]) for report in reports], reports
