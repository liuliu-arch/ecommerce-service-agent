"""故事课共享日志：标准级别、中文终端格式和安全学习摘要。"""

from __future__ import annotations

import inspect
import json
import logging
import logging.config
import os
import re
import time
from collections.abc import Callable, Mapping, Sequence
from contextvars import ContextVar, Token
from functools import wraps
from pathlib import Path
from typing import Any

LOGGER_NAME = "xiaozhe.course"
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
SECRET_KEYS = {"api_key", "apikey", "authorization", "password", "secret", "token", "access_token", "refresh_token", "cookie"}
PRIVATE_KEY_MARKS = ("phone", "mobile", "address", "email", "id_card", "identity_card", "bank_card")
PRIVATE_KEYS = {"nickname", "runtime_nickname", "runtime_user_id", "user_id", "customer_id", "customer_name", "user_name", "full_name"}
HIDDEN_REASONING_KEYS = {"reasoning_content", "hidden_reasoning", "hidden_cot", "chain_of_thought"}
VECTOR_ARRAY_KEYS = {"embedding", "embeddings", "vector", "vectors"}
THIRD_PARTY_LOGGERS = ("httpx", "httpcore", "openai", "chromadb")
_LOG_CONTEXT: ContextVar[tuple[str, str]] = ContextVar("course_log_context", default=("-", "-"))
_MODEL_CALLED: ContextVar[bool] = ContextVar("course_model_called", default=False)
_TEACHING_EVENT_COUNT: ContextVar[int] = ContextVar("course_teaching_event_count", default=0)
_CURRENT_LESSON_ID = "-"
_ACCESS_LOG_ENABLED = False
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+\-/=]+")
_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")
_CREDENTIAL = re.compile(r"(?i)((?:api[_-]?key|password|secret|access[_-]?token|refresh[_-]?token|cookie)\s*[:=]\s*)[^\s,，;；]+")
_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_ADDRESS = re.compile(r"(地址\s*[:：]\s*)[^\n,，;；]{4,80}")
_EMAIL = re.compile(r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b")


def _redact_text(value: str) -> str:
    value = _BEARER.sub("Bearer ***", value)
    value = _KEY.sub("sk-***", value)
    value = _CREDENTIAL.sub(r"\1***", value)
    value = _PHONE.sub("***手机号***", value)
    value = _ADDRESS.sub(r"\1***地址***", value)
    return _EMAIL.sub("***邮箱***", value)


def sanitize(value: Any) -> Any:
    """做教学日志的最小必要脱敏，同时保留可学习的业务结构。"""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            name = str(key).lower()
            normalized_name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
            if normalized_name in SECRET_KEYS or normalized_name.endswith((
                "_api_key", "_password", "_secret", "_token", "_authorization", "_cookie",
            )):
                result[str(key)] = "***敏感凭据***"
            elif normalized_name in PRIVATE_KEYS or normalized_name.endswith("_user_id") or any(
                mark in normalized_name for mark in PRIVATE_KEY_MARKS
            ):
                result[str(key)] = "***个人隐私***"
            elif name in HIDDEN_REASONING_KEYS:
                result[str(key)] = "***隐藏推理不记录***"
            elif name in VECTOR_ARRAY_KEYS and isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
                first = item[0] if item else []
                nested = isinstance(first, Sequence) and not isinstance(first, (str, bytes, bytearray))
                result[str(key)] = {"数组已省略": True, "输入数": len(item) if nested else 1,
                                    "维度": len(first) if nested else len(item)}
            else:
                result[str(key)] = sanitize(item)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (Mapping, list)):
                    return json.dumps(sanitize(parsed), ensure_ascii=False)
            except (TypeError, ValueError):
                pass
        return _redact_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _redact_text(str(value))


class CourseLogFilter(logging.Filter):
    def __init__(self, lesson_id: str) -> None:
        super().__init__()
        self.lesson_id = lesson_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.lesson_id = getattr(record, "lesson_id", _LOG_CONTEXT.get()[0] if _LOG_CONTEXT.get()[0] != "-" else self.lesson_id)
        record.event_code = getattr(record, "event_code", "GENERAL")
        record.session_id = getattr(record, "session_id", _LOG_CONTEXT.get()[1])
        record.msg = _redact_text(record.msg) if isinstance(record.msg, str) else record.msg
        if isinstance(record.args, Mapping):
            record.args = sanitize(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(sanitize(item) for item in record.args)
        return True


def _load_logging_env(backend_dir: Path) -> None:
    path = Path(os.getenv("AGENT_COURSE_ENV", str(backend_dir.parents[1] / ".env"))).expanduser()
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in {"AGENT_LOG_LEVEL", "AGENT_ACCESS_LOG"}:
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _lesson_id(backend_dir: Path) -> str:
    try:
        data = json.loads((backend_dir / "agent_capabilities.json").read_text(encoding="utf-8"))
        return str(data["lesson"]["id"])
    except (OSError, KeyError, TypeError, ValueError):
        return backend_dir.parent.name


def configure_course_logging(backend_dir: str | Path) -> None:
    """重复调用会替换旧 handler，不会重复输出。"""
    global _ACCESS_LOG_ENABLED, _CURRENT_LESSON_ID
    backend = Path(backend_dir).resolve()
    _load_logging_env(backend)
    raw_level = os.getenv("AGENT_LOG_LEVEL", "INFO").strip().upper()
    level = raw_level if raw_level in VALID_LEVELS else "INFO"
    _ACCESS_LOG_ENABLED = os.getenv("AGENT_ACCESS_LOG", "false").strip().lower() in {"1", "true", "yes", "on"}
    lesson_id = _lesson_id(backend)
    _CURRENT_LESSON_ID = lesson_id
    handler = {
        "class": "logging.StreamHandler", "stream": "ext://sys.stdout", "level": level,
        "formatter": "course_console", "filters": ["course_context"],
    }
    course_logger = {"handlers": ["course_console"], "level": level, "propagate": False}
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"course_context": {"()": CourseLogFilter, "lesson_id": lesson_id}},
        "formatters": {"course_console": {
            "format": "%(asctime)s.%(msecs)03d｜%(levelname)-7s｜%(event_code)s｜%(session_id)s｜%(message)s",
            "datefmt": "%H:%M:%S",
        }},
        "handlers": {"course_console": handler},
        "loggers": {
            LOGGER_NAME: course_logger,
            "uvicorn": course_logger,
            "uvicorn.error": {"level": level},
            "uvicorn.access": course_logger,
            **{name: {"handlers": ["course_console"], "level": "WARNING", "propagate": False}
               for name in THIRD_PARTY_LOGGERS},
        },
    })
    logger = logging.getLogger(LOGGER_NAME)
    if raw_level not in VALID_LEVELS:
        logger.warning("AGENT_LOG_LEVEL=%s 无效，已回退为 INFO", raw_level,
                       extra={"event_code": "LOG_LEVEL_INVALID"})
    logger.info("课程日志已启动，课次=%s，level=%s，access_log=%s", lesson_id, level, _ACCESS_LOG_ENABLED,
                extra={"event_code": "COURSE_LOGGING_READY"})

def course_access_log_enabled() -> bool:
    return _ACCESS_LOG_ENABLED


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return dict(value) if isinstance(value, Mapping) else {}


def _first(payload: Mapping[str, Any], *paths: str, default: Any = None) -> Any:
    for path in paths:
        current: Any = payload
        for part in path.split("."):
            current = current.get(part) if isinstance(current, Mapping) else None
        if current not in (None, "", [], {}):
            return current
    return default


def _tools(payload: Mapping[str, Any]) -> list[str]:
    names: list[str] = []
    for item in payload.get("tool_calls") or []:
        if isinstance(item, Mapping):
            name = item.get("tool_name") or _first(item, "action.tool_name")
            if name and str(name) not in names:
                names.append(str(name))
    return names


def _summary(result: Any, model_called: bool = False) -> str:
    data = _dump(result)
    citations = data.get("citations") or _first(data, "session_state.rag.citations", default=[])
    explicit_count = _first(data, "session_state.rag.citation_count")
    rag_count = explicit_count if explicit_count is not None else (
        len(citations) if citations else _first(
            data, "session_state.rag.retrieved_count", "session_state.rag.raw_retrieved_count",
            "session_state.rag.hit_count", default=0,
        )
    )
    intent = _first(data, "intent", "intent_result.intent", "route_plan.intent",
                    "session_state.intent_result.intent", "session_state.route_plan.intent", default="unknown")
    workflow = _first(data, "workflow.status", "session_state.workflow.pending_action",
                      "session_state.workflow.status", default="none")
    model = model_called or any(bool(_first(data, path)) for path in (
        "session_state.model_answer.used_model", "session_state.model.final_answer.used_model",
        "session_state.model.route_planner.used_model", "session_state.tool_calling.langchain.create_agent",
    ))
    return (f"意图={intent} → RAG={rag_count}"
            f" → Tool={','.join(_tools(data)) or 'none'} → Workflow={workflow}"
            f" → Model={'used' if model else 'not_used'}")


def _request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any | None:
    return next((item for item in (*args, *kwargs.values())
                 if hasattr(item, "session_id")), None)


def _begin(args: tuple[Any, ...], kwargs: dict[str, Any], lesson_id: str, operation: str) -> tuple[Token[tuple[str, str]], Token[bool], Token[int], float]:
    request = _request(args, kwargs)
    token = _LOG_CONTEXT.set((lesson_id, str(getattr(request, "session_id", "-"))))
    model_token = _MODEL_CALLED.set(False)
    teaching_token = _TEACHING_EVENT_COUNT.set(0)
    if operation == "chat":
        message = "收到聊天请求，输入长度=%d"
        params = (len(str(getattr(request, "user_message", ""))),)
    else:
        message, params = f"开始{operation}操作", ()
    event_code = "CHAT_REQUEST_STARTED" if operation == "chat" else f"{operation.upper()}_STARTED"
    logger = logging.getLogger(LOGGER_NAME)
    logger.info(message, *params, extra={"event_code": event_code})
    if request is not None:
        request_detail = vars(request) if hasattr(request, "__dict__") else request
        logger.debug("请求结构=%s", sanitize(request_detail), extra={"event_code": "REQUEST_DETAIL"})
    return token, model_token, teaching_token, time.perf_counter()


def _finish(result: Any, started: float, lesson_id: str, operation: str) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    data = _dump(result)
    if operation == "chat":
        summary = _summary(result, _MODEL_CALLED.get())
    else:
        status = _first(data, "status", "record.feedback_id", default="completed")
        reason = _first(data, "resume_result.reason", "result.reason", default="none")
        summary = f"操作={operation} → 状态={status} → 原因={reason}"
    event_code = "CHAT_PATH_SUMMARY" if operation == "chat" else f"{operation.upper()}_SUMMARY"
    logger.info("%s，耗时=%.1fms", summary, (time.perf_counter() - started) * 1000,
                extra={"event_code": event_code})
    fallback = _first(_dump(result), "session_state.model_answer.fallback_reason",
                      "session_state.model.final_answer.fallback_reason", "session_state.model.route_planner.fallback_reason")
    degradation = _first(data, "session_state.degradation.error_category") if _first(
        data, "degraded", "session_state.degradation.degraded", default=False,
    ) else None
    if fallback or degradation:
        event_code = "CHAT_DEGRADED" if operation == "chat" else f"{operation.upper()}_DEGRADED"
        logger.warning("本轮已降级或兜底，原因=%s", fallback or degradation,
                       extra={"event_code": event_code})
def _fail(exc: Exception, operation: str) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    event_code = "CHAT_REQUEST_FAILED" if operation == "chat" else f"{operation.upper()}_FAILED"
    logger.error("%s操作失败，异常类型=%s，原因=%s", operation, type(exc).__name__, str(exc),
                 exc_info=logger.isEnabledFor(logging.DEBUG), extra={"event_code": event_code})


def observe_operation(operation: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """记录 chat/resume/feedback 的起止、教学信号与错误。"""
    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        return _decorate_operation(func, operation)
    return decorate


def _decorate_operation(func: Callable[..., Any], operation: str) -> Callable[..., Any]:
    lesson_id = _CURRENT_LESSON_ID
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            token, model_token, teaching_token, started = _begin(args, kwargs, lesson_id, operation)
            try:
                result = await func(*args, **kwargs)
                _finish(result, started, lesson_id, operation)
                return result
            except Exception as exc:
                _fail(exc, operation)
                raise
            finally:
                _LOG_CONTEXT.reset(token)
                _MODEL_CALLED.reset(model_token)
                _TEACHING_EVENT_COUNT.reset(teaching_token)
        return async_wrapper

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token, model_token, teaching_token, started = _begin(args, kwargs, lesson_id, operation)
        try:
            result = func(*args, **kwargs)
            _finish(result, started, lesson_id, operation)
            return result
        except Exception as exc:
            _fail(exc, operation)
            raise
        finally:
            _LOG_CONTEXT.reset(token)
            _MODEL_CALLED.reset(model_token)
            _TEACHING_EVENT_COUNT.reset(teaching_token)
    return wrapper


def observe_chat(func: Callable[..., Any]) -> Callable[..., Any]:
    """用一处装饰器记录聊天请求，避免在 Agent 分支里堆日志。"""
    return _decorate_operation(func, "chat")


def log_course_event(event_code: str, summary: str, *, teaching: bool = False, **fields: Any) -> None:
    """在事件实际发生处打印教学日志；INFO 每轮最多保留 7 条关键事件。"""
    logger = logging.getLogger(LOGGER_NAME)
    level = logging.INFO if teaching else logging.DEBUG
    if not logger.isEnabledFor(level):
        return
    if teaching:
        count = _TEACHING_EVENT_COUNT.get()
        if count >= 7:
            level = logging.DEBUG
        else:
            _TEACHING_EVENT_COUNT.set(count + 1)
    caller = inspect.currentframe().f_back
    source = f"{caller.f_globals.get('__name__', '-')}.{caller.f_code.co_name}" if caller else "-"
    detail = sanitize(fields)
    message = f"{source}｜{summary}"
    if detail:
        message += f"：{detail}"
    logger.log(level, message, extra={"event_code": event_code})


def log_model_input(*, model: str, messages: Any, prompt_source: str) -> None:
    _MODEL_CALLED.set(True)
    logging.getLogger(LOGGER_NAME).debug("模型=%s，Prompt来源=%s，完整输入=%s", model, prompt_source,
                                         sanitize(messages), extra={"event_code": "MODEL_INPUT"})


def log_model_output(*, model: str, content: Any) -> Any:
    logging.getLogger(LOGGER_NAME).debug("模型=%s，完整输出=%s", model, sanitize(content),
                                         extra={"event_code": "MODEL_OUTPUT"})
    return content


def log_embedding_summary(*, model: str, input_count: int, dimensions: int) -> None:
    logging.getLogger(LOGGER_NAME).debug("Embedding模型=%s，输入数=%d，向量维度=%d", model, input_count,
                                         dimensions, extra={"event_code": "EMBEDDING_SUMMARY"})


def log_rerank_summary(*, model: str, scores: Sequence[float]) -> None:
    logging.getLogger(LOGGER_NAME).debug("Reranker模型=%s，候选数=%d，得分=%s", model, len(scores),
                                         [round(float(x), 4) for x in scores],
                                         extra={"event_code": "RERANK_SUMMARY"})


def log_tool_started(tool_name: str, arguments: Any) -> None:
    visible = dict(arguments) if isinstance(arguments, Mapping) else {"input": arguments}
    log_course_event("TOOL_STARTED", "受控工具开始执行", teaching=True,
                     tool_name=tool_name, argument_keys=sorted(visible))
    log_course_event("TOOL_INPUT", "工具收到的脱敏参数结构", tool_name=tool_name, arguments=visible)


def log_tool_finished(tool_name: str, result: Any) -> None:
    candidates = result if isinstance(result, tuple) else (result,)
    observation = next((item for item in reversed(candidates) if hasattr(item, "status")), None)
    log_course_event(
        "TOOL_FINISHED", "工具执行结束并返回可治理结果", teaching=True,
        tool_name=str(getattr(observation, "tool_name", tool_name)), status=getattr(observation, "status", "success"),
        attempts=getattr(observation, "attempts", 1), next_action=getattr(observation, "next_action", None),
        error_type=getattr(observation, "error_type", None) or getattr(observation, "error_category", None),
        observation_summary=getattr(observation, "output_summary", None) or getattr(observation, "summary", None),
    )
    log_course_event("TOOL_OUTPUT", "工具返回的脱敏结果结构", tool_name=tool_name, result=result)


def log_tool_failed(tool_name: str, exc: Exception) -> None:
    logging.getLogger(LOGGER_NAME).error(
        "工具执行失败，tool_name=%s，异常类型=%s，原因=%s",
        tool_name,
        type(exc).__name__,
        str(exc),
        extra={"event_code": "TOOL_FAILED"},
    )


def observe_tool_execution(func: Callable[..., Any]) -> Callable[..., Any]:
    """统一记录真实 Tool 函数的开始、结束和 DEBUG 结构，不介入工具决策。"""
    signature = inspect.signature(func)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        bound = signature.bind_partial(*args, **kwargs)
        action = next((value for value in bound.arguments.values() if hasattr(value, "tool_name")), None)
        tool_name = str(getattr(action, "tool_name", func.__name__))
        visible_inputs = {key: value for key, value in bound.arguments.items()
                          if key not in {"self", "request", "runtime_context", "runtime_user_id", "tool_specs"}}
        log_tool_started(tool_name, visible_inputs)
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            log_tool_failed(tool_name, exc)
            raise
        log_tool_finished(tool_name, result)
        return result

    return wrapper


def observe_evaluation(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        result = func(*args, **kwargs)
        results = _dump(result).get("results") or []
        passed = sum(bool(item.get("passed")) for item in results if isinstance(item, Mapping))
        logger = logging.getLogger(LOGGER_NAME)
        logger.info("Evaluation完成，总数=%d，通过=%d，耗时=%.1fms", len(results), passed,
                    (time.perf_counter() - started) * 1000, extra={"event_code": "EVAL_SUMMARY"})
        return result
    return wrapper
