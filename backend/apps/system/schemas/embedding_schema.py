from enum import Enum

from pydantic import BaseModel, Field


class EmbeddingProviderType(str, Enum):
    OPENAI_COMPATIBLE = "openai_compatible"
    LOCAL = "local"


class EmbeddingStartupBackfillPolicy(str, Enum):
    EAGER = "eager"
    DEFERRED = "deferred"
    MANUAL = "manual"


class EmbeddingState(str, Enum):
    DISABLED = "disabled"
    CONFIGURED_UNVERIFIED = "configured_unverified"
    VALIDATED_DISABLED = "validated_disabled"
    ENABLED = "enabled"
    REINDEX_REQUIRED = "reindex_required"
    VALIDATION_FAILED = "validation_failed"


class EmbeddingConfigPayload(BaseModel):
    provider_type: EmbeddingProviderType
    supplier_id: int | None = None
    model_name: str | None = None
    base_url: str | None = None
    api_key: str = ""
    api_key_configured: bool = False
    timeout_seconds: int = Field(default=30, ge=1)
    local_model: str | None = None
    startup_backfill_policy: EmbeddingStartupBackfillPolicy = (
        EmbeddingStartupBackfillPolicy.DEFERRED
    )


class EmbeddingValidationInfo(BaseModel):
    success: bool = False
    message: str = "Not validated yet"
    at: str | None = None


class EmbeddingStatusPayload(BaseModel):
    enabled: bool = False
    state: EmbeddingState = EmbeddingState.DISABLED
    reindex_required: bool = False
    reindex_reason: str | None = None
    last_validation: EmbeddingValidationInfo = Field(
        default_factory=EmbeddingValidationInfo
    )


class EmbeddingConfigResponse(BaseModel):
    config: EmbeddingConfigPayload
    status: EmbeddingStatusPayload


class EmbeddingConfigUpdateRequest(BaseModel):
    config: EmbeddingConfigPayload


class EmbeddingValidateRequest(BaseModel):
    use_saved_config: bool = True
    config: EmbeddingConfigPayload | None = None


class EmbeddingValidateResponse(BaseModel):
    success: bool
    state: EmbeddingState
    message: str
    validated_at: str | None = None


class EmbeddingToggleResponse(BaseModel):
    success: bool
    state: EmbeddingState
    message: str | None = None
