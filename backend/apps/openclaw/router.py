import asyncio
import base64
import json
import os
from typing import cast

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from apps.chat.api.chat import analysis_or_predict, question_answer_inner
from apps.chat.models.chat_model import ChatQuestion
from apps.datasource.crud.datasource import get_datasource_list
from apps.openclaw.contract import (
    AUTH_HEADER,
    OpenClawAnalysisRequest,
    OpenClawDatasourceListRequest,
    OpenClawErrorCode,
    OpenClawErrorEnvelope,
    OpenClawOperation,
    OpenClawQuestionRequest,
    OpenClawSessionBindRequest,
    OpenClawSuccessEnvelope,
)
from apps.openclaw.service import (
    OpenClawServiceError,
    authenticate_openclaw_service_token,
    bind_openclaw_session,
)
from apps.system.schemas.system_schema import UserInfoDTO
from common.core.config import settings
from common.core.deps import SessionDep

router = APIRouter(tags=["openclaw"], prefix="/openclaw")
_openclaw_capacity_lock = asyncio.Lock()
_openclaw_active_requests = 0


def _status_code_for_error(error_code: str) -> int:
    if error_code in {
        OpenClawErrorCode.AUTH_INVALID,
        OpenClawErrorCode.AUTH_EXPIRED,
    }:
        return 401
    if error_code == OpenClawErrorCode.AUTH_DISABLED:
        return 403
    if error_code == OpenClawErrorCode.SESSION_INVALID:
        return 400
    if error_code == OpenClawErrorCode.DATASOURCE_NOT_FOUND:
        return 404
    if error_code == OpenClawErrorCode.VALIDATION_ERROR:
        return 422
    if error_code == OpenClawErrorCode.EXECUTION_TIMEOUT:
        return 504
    if error_code == OpenClawErrorCode.CONCURRENCY_EXCEEDED:
        return 429
    if error_code == OpenClawErrorCode.INTEGRATION_DISABLED:
        return 503
    return 500


def _error_response(
    operation: str,
    error_code: str,
    message: str,
    *,
    detail: dict[str, object] | None = None,
) -> JSONResponse:
    envelope = OpenClawErrorEnvelope(
        operation=operation,
        error_code=error_code,
        message=message,
        detail=detail,
    )
    return JSONResponse(
        status_code=_status_code_for_error(error_code),
        content=envelope.model_dump(),
    )


def _success_response(operation: str, data: dict[str, object]) -> JSONResponse:
    envelope = OpenClawSuccessEnvelope(operation=operation, data=data)
    return JSONResponse(status_code=200, content=envelope.model_dump(mode="json"))


def _extract_json_response_payload(response: JSONResponse) -> dict[str, object]:
    raw_body_bytes = bytes(response.body)
    raw_body = cast(object, json.loads(raw_body_bytes.decode("utf-8")))
    if isinstance(raw_body, dict):
        return cast(dict[str, object], raw_body)
    return {"raw": raw_body}


def _enrich_payload_with_image_base64(
    payload: dict[str, object],
    *,
    include_image_base64: bool = False,
) -> dict[str, object]:
    if not include_image_base64:
        return payload
    image_url = payload.get("image_url")
    if not isinstance(image_url, str) or not image_url:
        return payload
    file_name = image_url.rsplit("/", 1)[-1]
    file_path = os.path.join(settings.MCP_IMAGE_PATH, file_name)
    if not os.path.isfile(file_path):
        return payload
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    payload["image_base64"] = encoded
    return payload


def _build_display_hint(payload: dict[str, object]) -> None:
    image_url = payload.get("image_url")
    if not isinstance(image_url, str) or not image_url:
        return

    chart = payload.get("chart")
    if not isinstance(chart, dict):
        return

    title = chart.get("title") or payload.get("title") or ""

    data_obj = payload.get("data")
    if not isinstance(data_obj, dict):
        return
    rows = data_obj.get("data")
    if not isinstance(rows, list) or not rows:
        payload["display_hint"] = f"📊 [点击查看图表]({image_url})"
        return

    axis = chart.get("axis")
    col_names: list[str] = []
    col_keys: list[str] = []

    if isinstance(axis, dict):
        x = axis.get("x")
        if isinstance(x, dict) and "name" in x and "value" in x:
            col_names.append(str(x["name"]))
            col_keys.append(str(x["value"]))
        y_list = axis.get("y")
        if isinstance(y_list, list):
            for y_item in y_list:
                if isinstance(y_item, dict) and "name" in y_item and "value" in y_item:
                    col_names.append(str(y_item["name"]))
                    col_keys.append(str(y_item["value"]))

    if not col_keys:
        fields = data_obj.get("fields")
        if isinstance(fields, list) and fields:
            col_names = [str(f) for f in fields]
            col_keys = col_names

    if not col_keys:
        first_row = rows[0]
        if isinstance(first_row, dict):
            col_keys = list(first_row.keys())
            col_names = col_keys

    header = "| " + " | ".join(col_names) + " |"
    separator = "| " + " | ".join("---" for _ in col_names) + " |"
    body_lines: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            cells = [str(row.get(k, "")) for k in col_keys]
            body_lines.append("| " + " | ".join(cells) + " |")

    parts: list[str] = []
    if title:
        parts.append(f"## {title}")
        parts.append("")
    parts.append(header)
    parts.append(separator)
    parts.extend(body_lines)
    parts.append("")
    parts.append(f"📊 [点击查看图表]({image_url})")

    payload["display_hint"] = "\n".join(parts)


def _normalize_message(value: object, fallback: str) -> str:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return fallback


def _classify_execution_error(message: str, *, status_code: int | None = None) -> str:
    normalized = message.lower()
    if status_code == 504 or "timeout" in normalized or "timed out" in normalized:
        return OpenClawErrorCode.EXECUTION_TIMEOUT
    if "datasource" in normalized or "data source" in normalized:
        return OpenClawErrorCode.DATASOURCE_NOT_FOUND
    if any(
        marker in normalized
        for marker in (
            "llm",
            "model",
            "openai",
            "anthropic",
            "claude",
            "gemini",
            "qwen",
            "deepseek",
        )
    ):
        return OpenClawErrorCode.LLM_FAILURE
    return OpenClawErrorCode.EXECUTION_FAILURE


def _build_execution_error_response(
    operation: str,
    *,
    message: object,
    fallback_message: str,
    detail: dict[str, object] | None = None,
    status_code: int | None = None,
) -> JSONResponse:
    normalized_message = _normalize_message(message, fallback_message)
    return _error_response(
        operation,
        _classify_execution_error(normalized_message, status_code=status_code),
        normalized_message,
        detail=detail,
    )


def _timeout_error_response(
    operation: str, *, detail: dict[str, object]
) -> JSONResponse:
    return _error_response(
        operation,
        OpenClawErrorCode.EXECUTION_TIMEOUT,
        f"Operation exceeded {settings.OPENCLAW_REQUEST_TIMEOUT_SECONDS} seconds",
        detail=detail,
    )


def _integration_disabled_response(operation: str) -> JSONResponse:
    return _error_response(
        operation,
        OpenClawErrorCode.INTEGRATION_DISABLED,
        "OpenClaw integration is disabled",
    )


async def _try_acquire_request_slot(operation: str) -> JSONResponse | None:
    global _openclaw_active_requests

    if settings.OPENCLAW_MAX_CONCURRENT_REQUESTS <= 0:
        return None

    async with _openclaw_capacity_lock:
        if _openclaw_active_requests >= settings.OPENCLAW_MAX_CONCURRENT_REQUESTS:
            return _error_response(
                operation,
                OpenClawErrorCode.CONCURRENCY_EXCEEDED,
                "OpenClaw concurrency limit exceeded",
                detail={
                    "max_concurrent_requests": settings.OPENCLAW_MAX_CONCURRENT_REQUESTS
                },
            )
        _openclaw_active_requests += 1
    return None


async def _release_request_slot() -> None:
    global _openclaw_active_requests

    if settings.OPENCLAW_MAX_CONCURRENT_REQUESTS <= 0:
        return

    async with _openclaw_capacity_lock:
        if _openclaw_active_requests > 0:
            _openclaw_active_requests -= 1


def _operation_for_path(path: str) -> str | None:
    normalized_path = path
    if normalized_path.startswith(settings.API_V1_STR):
        normalized_path = normalized_path[len(settings.API_V1_STR) :]

    if normalized_path == "/openclaw/session/bind":
        return OpenClawOperation.SESSION_BIND
    if normalized_path == "/openclaw/question":
        return OpenClawOperation.QUESTION_EXECUTE
    if normalized_path == "/openclaw/analysis":
        return OpenClawOperation.ANALYSIS_EXECUTE
    if normalized_path == "/openclaw/datasources":
        return OpenClawOperation.DATASOURCE_LIST
    return None


def openclaw_validation_error_response(
    request: Request, exc: RequestValidationError
) -> JSONResponse | None:
    operation = _operation_for_path(request.url.path)
    if operation is None:
        return None

    return _error_response(
        operation,
        OpenClawErrorCode.VALIDATION_ERROR,
        "Request validation failed",
        detail={"errors": cast(object, exc.errors())},
    )


async def _authenticate_request(
    session: SessionDep, request: Request, operation: str
) -> tuple[JSONResponse | None, UserInfoDTO | None]:
    try:
        current_user = await authenticate_openclaw_service_token(
            session,
            request.headers.get(AUTH_HEADER),
        )
    except OpenClawServiceError as exc:
        return (
            _error_response(
                operation,
                exc.error_code,
                exc.message,
                detail=exc.detail,
            ),
            None,
        )
    request.state.current_user = current_user
    return None, current_user


@router.post(
    "/session/bind",
    operation_id="openclaw_session_bind",
    summary="OpenClaw bind session",
)
async def bind_session(
    request: Request,
    bind_request: OpenClawSessionBindRequest,
    session: SessionDep,
) -> JSONResponse:
    if not settings.OPENCLAW_ENABLED:
        return _integration_disabled_response(OpenClawOperation.SESSION_BIND)

    error_response, current_user = await _authenticate_request(
        session, request, OpenClawOperation.SESSION_BIND
    )
    if error_response is not None:
        return error_response
    if current_user is None:
        return _error_response(
            OpenClawOperation.SESSION_BIND,
            OpenClawErrorCode.AUTH_INVALID,
            "Authenticated user context is unavailable",
        )

    capacity_error = await _try_acquire_request_slot(OpenClawOperation.SESSION_BIND)
    if capacity_error is not None:
        return capacity_error

    try:
        binding = bind_openclaw_session(session, current_user, bind_request)
    except OpenClawServiceError as exc:
        return _error_response(
            OpenClawOperation.SESSION_BIND,
            exc.error_code,
            exc.message,
            detail=exc.detail,
        )
    except Exception as exc:
        return _error_response(
            OpenClawOperation.SESSION_BIND,
            OpenClawErrorCode.INTERNAL_ERROR,
            "Session binding failed",
            detail={"reason": str(exc)},
        )
    finally:
        await _release_request_slot()

    return _success_response(
        OpenClawOperation.SESSION_BIND,
        {
            "conversation_id": binding.conversation_id,
            "chat_id": binding.chat_id,
            "reused": binding.reused,
            "user_id": binding.user_id,
            "workspace_id": binding.workspace_id,
            "datasource_id": binding.datasource_id,
        },
    )


@router.post(
    "/question",
    operation_id="openclaw_question_execute",
    summary="OpenClaw execute question",
)
async def ask_question(
    request: Request,
    question_request: OpenClawQuestionRequest,
    session: SessionDep,
) -> JSONResponse:
    if not settings.OPENCLAW_ENABLED:
        return _integration_disabled_response(OpenClawOperation.QUESTION_EXECUTE)

    error_response, current_user = await _authenticate_request(
        session, request, OpenClawOperation.QUESTION_EXECUTE
    )
    if error_response is not None:
        return error_response
    if current_user is None:
        return _error_response(
            OpenClawOperation.QUESTION_EXECUTE,
            OpenClawErrorCode.AUTH_INVALID,
            "Authenticated user context is unavailable",
        )

    capacity_error = await _try_acquire_request_slot(OpenClawOperation.QUESTION_EXECUTE)
    if capacity_error is not None:
        return capacity_error

    try:
        binding = bind_openclaw_session(
            session,
            current_user,
            OpenClawSessionBindRequest(
                conversation_id=question_request.conversation_id,
                chat_id=question_request.chat_id,
                datasource_id=question_request.datasource_id,
                language=question_request.language,
            ),
        )
        response = await asyncio.wait_for(
            question_answer_inner(
                session=session,
                current_user=current_user,
                request_question=ChatQuestion(
                    chat_id=binding.chat_id,
                    question=question_request.question,
                    datasource_id=question_request.datasource_id,
                    lang=question_request.language,
                ),
                current_assistant=None,
                in_chat=False,
                stream=False,
            ),
            timeout=settings.OPENCLAW_REQUEST_TIMEOUT_SECONDS,
        )
    except OpenClawServiceError as exc:
        return _error_response(
            OpenClawOperation.QUESTION_EXECUTE,
            exc.error_code,
            exc.message,
            detail=exc.detail,
        )
    except TimeoutError:
        return _timeout_error_response(
            OpenClawOperation.QUESTION_EXECUTE,
            detail={"timeout_seconds": settings.OPENCLAW_REQUEST_TIMEOUT_SECONDS},
        )
    except Exception as exc:
        return _build_execution_error_response(
            OpenClawOperation.QUESTION_EXECUTE,
            message=str(exc),
            fallback_message="Question execution failed",
            detail={"chat_id": question_request.chat_id},
        )
    finally:
        await _release_request_slot()

    if not isinstance(response, JSONResponse):
        return _error_response(
            OpenClawOperation.QUESTION_EXECUTE,
            OpenClawErrorCode.EXECUTION_FAILURE,
            "Question execution did not return a JSON response",
        )

    payload = _extract_json_response_payload(response)
    if response.status_code >= 400:
        return _build_execution_error_response(
            OpenClawOperation.QUESTION_EXECUTE,
            message=payload.get("message", "Question execution failed"),
            fallback_message="Question execution failed",
            detail={"upstream": payload, "chat_id": binding.chat_id},
            status_code=response.status_code,
        )

    _build_display_hint(payload)
    return _success_response(
        OpenClawOperation.QUESTION_EXECUTE,
        {
            "conversation_id": question_request.conversation_id,
            "chat_id": binding.chat_id,
            "result": _enrich_payload_with_image_base64(
                payload,
                include_image_base64=question_request.include_image_base64,
            ),
        },
    )


@router.post(
    "/analysis",
    operation_id="openclaw_analysis_execute",
    summary="OpenClaw execute analysis",
)
async def run_analysis(
    request: Request,
    analysis_request: OpenClawAnalysisRequest,
    session: SessionDep,
) -> JSONResponse:
    if not settings.OPENCLAW_ENABLED:
        return _integration_disabled_response(OpenClawOperation.ANALYSIS_EXECUTE)

    error_response, current_user = await _authenticate_request(
        session, request, OpenClawOperation.ANALYSIS_EXECUTE
    )
    if error_response is not None:
        return error_response
    if current_user is None:
        return _error_response(
            OpenClawOperation.ANALYSIS_EXECUTE,
            OpenClawErrorCode.AUTH_INVALID,
            "Authenticated user context is unavailable",
        )

    capacity_error = await _try_acquire_request_slot(OpenClawOperation.ANALYSIS_EXECUTE)
    if capacity_error is not None:
        return capacity_error

    try:
        _ = bind_openclaw_session(
            session,
            current_user,
            OpenClawSessionBindRequest(
                conversation_id=analysis_request.conversation_id,
                chat_id=analysis_request.chat_id,
                language=analysis_request.language,
            ),
        )
        response = await asyncio.wait_for(
            analysis_or_predict(
                session=session,
                current_user=current_user,
                chat_record_id=analysis_request.record_id,
                action_type=analysis_request.action_type,
                current_assistant=None,
                in_chat=False,
                stream=False,
            ),
            timeout=settings.OPENCLAW_REQUEST_TIMEOUT_SECONDS,
        )
    except OpenClawServiceError as exc:
        return _error_response(
            OpenClawOperation.ANALYSIS_EXECUTE,
            exc.error_code,
            exc.message,
            detail=exc.detail,
        )
    except TimeoutError:
        return _timeout_error_response(
            OpenClawOperation.ANALYSIS_EXECUTE,
            detail={"timeout_seconds": settings.OPENCLAW_REQUEST_TIMEOUT_SECONDS},
        )
    except Exception as exc:
        return _build_execution_error_response(
            OpenClawOperation.ANALYSIS_EXECUTE,
            message=str(exc),
            fallback_message="Analysis execution failed",
            detail={
                "chat_id": analysis_request.chat_id,
                "record_id": analysis_request.record_id,
            },
        )
    finally:
        await _release_request_slot()

    if not isinstance(response, JSONResponse):
        return _error_response(
            OpenClawOperation.ANALYSIS_EXECUTE,
            OpenClawErrorCode.EXECUTION_FAILURE,
            "Analysis execution did not return a JSON response",
        )

    payload = _extract_json_response_payload(response)
    if response.status_code >= 400:
        return _build_execution_error_response(
            OpenClawOperation.ANALYSIS_EXECUTE,
            message=payload.get("message", "Analysis execution failed"),
            fallback_message="Analysis execution failed",
            detail={
                "upstream": payload,
                "chat_id": analysis_request.chat_id,
                "record_id": analysis_request.record_id,
            },
            status_code=response.status_code,
        )

    _build_display_hint(payload)
    return _success_response(
        OpenClawOperation.ANALYSIS_EXECUTE,
        {
            "conversation_id": analysis_request.conversation_id,
            "chat_id": analysis_request.chat_id,
            "record_id": analysis_request.record_id,
            "action_type": analysis_request.action_type,
            "result": _enrich_payload_with_image_base64(
                payload,
                include_image_base64=analysis_request.include_image_base64,
            ),
        },
    )


@router.post(
    "/datasources",
    operation_id="openclaw_datasource_list",
    summary="OpenClaw list datasources",
)
async def list_datasources(
    request: Request,
    datasource_request: OpenClawDatasourceListRequest,
    session: SessionDep,
) -> JSONResponse:
    if not settings.OPENCLAW_ENABLED:
        return _integration_disabled_response(OpenClawOperation.DATASOURCE_LIST)

    error_response, current_user = await _authenticate_request(
        session, request, OpenClawOperation.DATASOURCE_LIST
    )
    if error_response is not None:
        return error_response
    if current_user is None:
        return _error_response(
            OpenClawOperation.DATASOURCE_LIST,
            OpenClawErrorCode.AUTH_INVALID,
            "Authenticated user context is unavailable",
        )

    capacity_error = await _try_acquire_request_slot(OpenClawOperation.DATASOURCE_LIST)
    if capacity_error is not None:
        return capacity_error

    datasource_items: list[dict[str, object]] = []
    try:
        for item in get_datasource_list(session=session, user=current_user):
            item_data = dict(item.model_dump(mode="json"))
            item_data.pop("embedding", None)
            item_data.pop("table_relation", None)
            item_data.pop("recommended_config", None)
            item_data.pop("configuration", None)
            datasource_items.append(item_data)
    except Exception as exc:
        return _build_execution_error_response(
            OpenClawOperation.DATASOURCE_LIST,
            message=str(exc),
            fallback_message="Datasource listing failed",
        )
    finally:
        await _release_request_slot()

    return _success_response(
        OpenClawOperation.DATASOURCE_LIST,
        {
            "conversation_id": datasource_request.conversation_id,
            "items": cast(object, datasource_items),
        },
    )
