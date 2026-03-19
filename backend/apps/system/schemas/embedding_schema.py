from enum import Enum

from pydantic import BaseModel, Field, model_validator


class EmbeddingProvider(str, Enum):
    REMOTE = "remote"
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
    provider: EmbeddingProvider
    remote_base_url: str | None = None
    remote_api_key: str = ""
    remote_api_key_configured: bool = False
    remote_model: str | None = None
    remote_timeout_seconds: int = Field(default=30, ge=1)
    local_model: str | None = None
    startup_backfill_policy: EmbeddingStartupBackfillPolicy = (
        EmbeddingStartupBackfillPolicy.DEFERRED
    )

    @model_validator(mode="after")
    def validate_provider_specific_fields(self) -> "EmbeddingConfigPayload":
        if self.provider == EmbeddingProvider.REMOTE:
            if not self.remote_base_url:
                raise ValueError("remote_base_url is required for remote provider")
            if not self.remote_model:
                raise ValueError("remote_model is required for remote provider")
        if self.provider == EmbeddingProvider.LOCAL and not self.local_model:
            raise ValueError("local_model is required for local provider")
        return self


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
