import json
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, SecretStr
from sqlmodel import Session, col, select
from typing_extensions import override

from apps.system.models.system_model import AiModelDetail
from common.core.db import engine
from common.utils.crypto import sqlbot_decrypt
from common.utils.utils import prepare_model_arg

if TYPE_CHECKING:
    from langchain.chat_models.base import BaseChatModel
    from langchain_community.llms import VLLMOpenAI
    from langchain_openai import AzureChatOpenAI

    from apps.ai_model.openai.llm import BaseChatOpenAI
else:
    BaseChatModel = Any
    VLLMOpenAI = Any
    AzureChatOpenAI = Any
    BaseChatOpenAI = Any

# from langchain_community.llms import Tongyi, VLLM


class LLMConfig(BaseModel):
    """Base configuration class for large language models"""

    model_id: int | None = None
    model_type: str  # Model type: openai/tongyi/vllm etc.
    model_name: str  # Specific model name
    api_key: str | None = None
    api_base_url: str | None = None
    additional_params: dict[str, Any] = {}

    class Config:
        frozen: bool = True

    @override
    def __hash__(self) -> int:
        hashable_params = json.dumps(
            self.additional_params, sort_keys=True, default=str
        )

        return hash(
            (
                self.model_id,
                self.model_type,
                self.model_name,
                self.api_key,
                self.api_base_url,
                hashable_params,
            )
        )


class BaseLLM(ABC):
    """Abstract base class for large language models"""

    config: LLMConfig
    _llm: BaseChatModel

    def __init__(self, config: LLMConfig):
        self.config = config
        self._llm = self._init_llm()

    @abstractmethod
    def _init_llm(self) -> BaseChatModel:
        """Initialize specific large language model instance"""
        pass

    @property
    def llm(self) -> BaseChatModel:
        """Return the langchain LLM instance"""
        return self._llm


class OpenAIvLLM(BaseLLM):
    @override
    def _init_llm(self) -> BaseChatModel:
        vllm_cls = import_module("langchain_community.llms").VLLMOpenAI
        llm = vllm_cls(
            openai_api_key=self.config.api_key or "Empty",
            openai_api_base=self.config.api_base_url,
            model_name=self.config.model_name,
            streaming=True,
            **self.config.additional_params,
        )
        return cast(BaseChatModel, llm)


class OpenAIAzureLLM(BaseLLM):
    @override
    def _init_llm(self) -> AzureChatOpenAI:
        azure_chat_openai_cls = import_module("langchain_openai").AzureChatOpenAI
        params = dict(self.config.additional_params)
        api_version_raw = params.pop("api_version", None)
        deployment_name_raw = params.pop("deployment_name", None)
        api_version = api_version_raw if isinstance(api_version_raw, str) else None
        deployment_name = (
            deployment_name_raw if isinstance(deployment_name_raw, str) else None
        )
        return cast(
            AzureChatOpenAI,
            azure_chat_openai_cls(
                azure_endpoint=self.config.api_base_url,
                api_key=SecretStr(self.config.api_key) if self.config.api_key else None,
                model=self.config.model_name,
                api_version=api_version,
                azure_deployment=deployment_name,
                streaming=True,
                **params,
            ),
        )


class OpenAILLM(BaseLLM):
    @override
    def _init_llm(self) -> BaseChatModel:
        base_chat_openai_cls = import_module("apps.ai_model.openai.llm").BaseChatOpenAI
        return cast(
            BaseChatModel,
            base_chat_openai_cls(
                model=self.config.model_name,
                api_key=SecretStr(self.config.api_key) if self.config.api_key else None,
                base_url=self.config.api_base_url,
                stream_usage=True,
                **self.config.additional_params,
            ),
        )

    def generate(self, prompt: str) -> str:
        return str(self.llm.invoke(prompt).content)


class LLMFactory:
    """Large Language Model Factory Class"""

    _llm_types: dict[str, type[BaseLLM]] = {
        "openai": OpenAILLM,
        "tongyi": OpenAILLM,
        "vllm": OpenAIvLLM,
        "azure": OpenAIAzureLLM,
    }

    @classmethod
    @lru_cache(maxsize=32)
    def create_llm(cls, config: LLMConfig) -> BaseLLM:
        llm_class = cls._llm_types.get(config.model_type)
        if not llm_class and config.model_type == "ci_deterministic":
            deterministic_module = import_module("apps.ai_model.ci_deterministic")
            llm_class = cast(type[BaseLLM], deterministic_module.llm_class())
            cls.register_llm(config.model_type, llm_class)
        if not llm_class:
            raise ValueError(f"Unsupported LLM type: {config.model_type}")
        return llm_class(config)

    @classmethod
    def register_llm(cls, model_type: str, llm_class: type[BaseLLM]) -> None:
        """Register new model type"""
        cls._llm_types[model_type] = llm_class


#  todo
""" def get_llm_config(aimodel: AiModelDetail) -> LLMConfig:
    config = LLMConfig(
        model_type="openai",
        model_name=aimodel.name,
        api_key=aimodel.api_key,
        api_base_url=aimodel.endpoint,
        additional_params={"temperature": aimodel.temperature}
    )
    return config """


async def get_default_config() -> LLMConfig:
    with Session(engine) as session:
        db_model = session.exec(
            select(AiModelDetail).where(col(AiModelDetail.default_model).is_(True))
        ).first()
        if not db_model:
            raise Exception("The system default model has not been set")

        additional_params: dict[str, Any] = {}
        if db_model.config:
            try:
                config_parsed = cast(object, json.loads(db_model.config))
                config_raw = (
                    cast(list[dict[str, object]], config_parsed)
                    if isinstance(config_parsed, list)
                    else []
                )
                additional_params = {
                    str(item["key"]): prepare_model_arg(item.get("val"))
                    for item in config_raw
                    if "key" in item and "val" in item
                }
            except Exception:
                pass
        if not db_model.api_domain.startswith("http"):
            db_model.api_domain = await sqlbot_decrypt(db_model.api_domain)
            if db_model.api_key:
                db_model.api_key = await sqlbot_decrypt(db_model.api_key)

        config = LLMConfig(
            model_id=db_model.id,
            model_type="openai" if db_model.protocol == 1 else "vllm",
            model_name=db_model.base_model,
            api_key=db_model.api_key,
            api_base_url=db_model.api_domain,
            additional_params=additional_params,
        )
        if os.getenv("SQLBOT_CI_DETERMINISTIC_LLM", "0") == "1":
            deterministic_module = import_module("apps.ai_model.ci_deterministic")
            return cast(
                LLMConfig, deterministic_module.build_ci_deterministic_config(config)
            )
        return config
