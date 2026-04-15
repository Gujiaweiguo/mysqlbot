from pydantic import ValidationError

from apps.openclaw.contract import (
    AUTH_HEADER,
    AUTH_SCHEME,
    CONTRACT_ROLE_STATEMENT,
    CONTRACT_VERSION,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TRANSPORT,
    STREAMING_SUPPORT,
    OpenClawAnalysisRequest,
    OpenClawDatasourceListRequest,
    OpenClawErrorEnvelope,
    OpenClawQuestionRequest,
    OpenClawSessionBindRequest,
    OpenClawSuccessEnvelope,
    all_openclaw_error_codes,
    all_openclaw_operations,
)


def test_contract_constants_lock_v1_defaults() -> None:
    assert CONTRACT_VERSION == "v1"
    assert DEFAULT_TRANSPORT == "http-json"
    assert DEFAULT_TIMEOUT_SECONDS == 120
    assert STREAMING_SUPPORT is False
    assert AUTH_HEADER == "X-SQLBOT-ASK-TOKEN"
    assert AUTH_SCHEME == "sk"
    assert "sole NL-query/analysis engine" in CONTRACT_ROLE_STATEMENT


def test_operation_registry_is_unique() -> None:
    operations = all_openclaw_operations()
    assert operations == (
        "session.bind",
        "question.execute",
        "analysis.execute",
        "datasource.list",
    )
    assert len(operations) == len(set(operations))


def test_error_code_registry_is_unique() -> None:
    error_codes = all_openclaw_error_codes()
    assert len(error_codes) == len(set(error_codes))
    assert "AUTH_INVALID" in error_codes
    assert "EXECUTION_TIMEOUT" in error_codes


def test_request_models_encode_versioned_operations() -> None:
    bind_request = OpenClawSessionBindRequest(conversation_id="conv-1")
    question_request = OpenClawQuestionRequest(
        conversation_id="conv-1",
        question="show sales",
    )
    analysis_request = OpenClawAnalysisRequest(
        conversation_id="conv-1",
        chat_id=1,
        record_id=2,
    )
    datasource_request = OpenClawDatasourceListRequest(conversation_id="conv-1")

    assert bind_request.version == CONTRACT_VERSION
    assert bind_request.operation == "session.bind"
    assert question_request.operation == "question.execute"
    assert analysis_request.operation == "analysis.execute"
    assert datasource_request.operation == "datasource.list"


def test_request_models_forbid_unknown_fields() -> None:
    try:
        _ = OpenClawQuestionRequest.model_validate(
            {
                "conversation_id": "conv-1",
                "question": "show sales",
                "unknown": "boom",
            }
        )
    except ValidationError as exc:
        assert "Extra inputs are not permitted" in str(exc)
    else:
        raise AssertionError("ValidationError expected for unknown fields")


def test_success_envelope_shape_is_stable() -> None:
    envelope = OpenClawSuccessEnvelope(
        operation="question.execute",
        data={"chat_id": 1, "record_id": 2},
    )

    assert envelope.model_dump() == {
        "version": "v1",
        "status": "success",
        "operation": "question.execute",
        "data": {"chat_id": 1, "record_id": 2},
    }


def test_error_envelope_shape_is_stable() -> None:
    envelope = OpenClawErrorEnvelope(
        operation="question.execute",
        error_code="AUTH_INVALID",
        message="Invalid credential",
        detail={"header": AUTH_HEADER},
    )

    assert envelope.model_dump() == {
        "version": "v1",
        "status": "error",
        "operation": "question.execute",
        "error_code": "AUTH_INVALID",
        "message": "Invalid credential",
        "detail": {"header": AUTH_HEADER},
    }
