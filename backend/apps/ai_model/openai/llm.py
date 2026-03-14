from collections.abc import Iterator, Mapping
from typing import cast

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    BaseMessageChunk,
    ChatMessageChunk,
    FunctionMessageChunk,
    HumanMessageChunk,
    SystemMessageChunk,
)
from langchain_core.messages.ai import (
    InputTokenDetails,
    OutputTokenDetails,
    UsageMetadata,
)
from langchain_core.messages.tool import (
    ToolCallChunk,
    ToolMessageChunk,
    tool_call_chunk,
)
from langchain_core.outputs import ChatGenerationChunk
from langchain_core.outputs.chat_generation import ChatGeneration
from langchain_core.runnables import RunnableConfig, ensure_config
from langchain_openai import ChatOpenAI
from typing_extensions import override

ObjectDict = dict[str, object]


def _as_object_dict(value: object) -> ObjectDict | None:
    return cast(ObjectDict, value) if isinstance(value, dict) else None


def _as_object_list(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return cast(list[object], value)


def _get_str(mapping: Mapping[str, object], key: str) -> str | None:
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _get_int(mapping: Mapping[str, object], key: str) -> int | None:
    value = mapping.get(key)
    return value if isinstance(value, int) else None


def _create_usage_metadata(oai_token_usage: Mapping[str, object]) -> UsageMetadata:
    input_tokens = _get_int(oai_token_usage, "prompt_tokens") or 0
    output_tokens = _get_int(oai_token_usage, "completion_tokens") or 0
    total_tokens = _get_int(oai_token_usage, "total_tokens") or (
        input_tokens + output_tokens
    )
    prompt_details = _as_object_dict(oai_token_usage.get("prompt_tokens_details")) or {}
    completion_details = (
        _as_object_dict(oai_token_usage.get("completion_tokens_details")) or {}
    )
    input_token_details = cast(
        InputTokenDetails,
        {
            key: value
            for key, value in {
                "audio": _get_int(prompt_details, "audio_tokens"),
                "cache_read": _get_int(prompt_details, "cached_tokens"),
            }.items()
            if value is not None
        },
    )
    output_token_details = cast(
        OutputTokenDetails,
        {
            key: value
            for key, value in {
                "audio": _get_int(completion_details, "audio_tokens"),
                "reasoning": _get_int(completion_details, "reasoning_tokens"),
            }.items()
            if value is not None
        },
    )
    return UsageMetadata(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        input_token_details=input_token_details,
        output_token_details=output_token_details,
    )


def _convert_delta_to_message_chunk(
    _dict: Mapping[str, object], default_class: type[BaseMessageChunk]
) -> BaseMessageChunk:
    id_ = _get_str(_dict, "id")
    role = _get_str(_dict, "role") or ""
    content = _get_str(_dict, "content") or ""
    additional_kwargs: ObjectDict = {}
    # 兼容 reasoning_content (DeepSeek等) 和 reasoning (Ollama/LMStudio GPT-OSS) 两种字段
    reasoning_content = _dict.get("reasoning_content")
    if not reasoning_content:
        reasoning_content = _dict.get("reasoning")
    if reasoning_content:
        additional_kwargs["reasoning_content"] = reasoning_content
    function_call_raw = _as_object_dict(_dict.get("function_call"))
    if function_call_raw is not None:
        function_call = dict(function_call_raw)
        if function_call.get("name") is None:
            function_call["name"] = ""
        additional_kwargs["function_call"] = function_call
    tool_call_chunks: list[ToolCallChunk] = []
    raw_tool_calls = _as_object_list(_dict.get("tool_calls"))
    if raw_tool_calls:
        additional_kwargs["tool_calls"] = raw_tool_calls
        for raw_tool_call in raw_tool_calls:
            rtc = _as_object_dict(raw_tool_call)
            if rtc is None:
                continue
            function_payload = _as_object_dict(rtc.get("function"))
            if function_payload is None:
                continue
            tool_call_chunks.append(
                tool_call_chunk(
                    name=_get_str(function_payload, "name"),
                    args=_get_str(function_payload, "arguments"),
                    id=_get_str(rtc, "id"),
                    index=_get_int(rtc, "index"),
                )
            )

    if role == "user" or default_class == HumanMessageChunk:
        return HumanMessageChunk(content=content, id=id_)
    elif role == "assistant" or default_class == AIMessageChunk:
        return AIMessageChunk(
            content=content,
            additional_kwargs=additional_kwargs,
            id=id_,
            tool_call_chunks=tool_call_chunks,
        )
    elif role in ("system", "developer") or default_class == SystemMessageChunk:
        if role == "developer":
            additional_kwargs = {"__openai_role__": "developer"}
        else:
            additional_kwargs = {}
        return SystemMessageChunk(
            content=content, id=id_, additional_kwargs=additional_kwargs
        )
    elif role == "function" or default_class == FunctionMessageChunk:
        return FunctionMessageChunk(
            content=content, name=_get_str(_dict, "name") or "", id=id_
        )
    elif role == "tool" or default_class == ToolMessageChunk:
        return ToolMessageChunk(
            content=content, tool_call_id=_get_str(_dict, "tool_call_id") or "", id=id_
        )
    elif role or default_class == ChatMessageChunk:
        return ChatMessageChunk(content=content, role=role, id=id_)
    else:
        return ChatMessageChunk(content=content, role="assistant", id=id_)


class BaseChatOpenAI(ChatOpenAI):
    usage_metadata: UsageMetadata | dict[str, object] = {}

    # custom_get_token_ids = custom_get_token_ids

    def get_last_generation_info(self) -> UsageMetadata | dict[str, object] | None:
        return self.usage_metadata

    @override
    def _stream(self, *args: object, **kwargs: object) -> Iterator[ChatGenerationChunk]:
        kwargs["stream_usage"] = True
        for chunk in super()._stream(*args, **kwargs):
            if (
                isinstance(chunk.message, AIMessageChunk)
                and chunk.message.usage_metadata is not None
            ):
                self.usage_metadata = dict(chunk.message.usage_metadata)
            yield chunk

    @override
    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict[str, object],
        default_chunk_class: type[BaseMessageChunk],
        base_generation_info: dict[str, object] | None,
    ) -> ChatGenerationChunk | None:
        if chunk.get("type") == "content.delta":  # from beta.chat.completions.stream
            return None
        token_usage = _as_object_dict(chunk.get("usage"))
        chunk_payload = _as_object_dict(chunk.get("chunk")) or {}
        choices = (
            _as_object_list(chunk.get("choices"))
            # from beta.chat.completions.stream
            or _as_object_list(chunk_payload.get("choices"))
        )

        usage_metadata: UsageMetadata | None = (
            _create_usage_metadata(token_usage)
            if token_usage and token_usage.get("prompt_tokens")
            else None
        )
        if len(choices) == 0:
            # logprobs is implicitly None
            empty_message: BaseMessageChunk
            if default_chunk_class == AIMessageChunk:
                empty_message = AIMessageChunk(
                    content="", usage_metadata=usage_metadata
                )
            else:
                empty_message = ChatMessageChunk(content="", role="assistant")
            generation_chunk = ChatGenerationChunk(message=empty_message)
            return generation_chunk

        choice = choices[0]
        choice_dict = _as_object_dict(choice)
        if choice_dict is None:
            return None
        delta = _as_object_dict(choice_dict.get("delta"))
        if delta is None:
            return None

        message_chunk = _convert_delta_to_message_chunk(delta, default_chunk_class)
        generation_info = {**base_generation_info} if base_generation_info else {}

        if finish_reason := _get_str(choice_dict, "finish_reason"):
            generation_info["finish_reason"] = finish_reason
            if model_name := _get_str(chunk, "model"):
                generation_info["model_name"] = model_name
            if system_fingerprint := _get_str(chunk, "system_fingerprint"):
                generation_info["system_fingerprint"] = system_fingerprint

        logprobs = choice_dict.get("logprobs")
        if logprobs:
            generation_info["logprobs"] = logprobs

        if usage_metadata and isinstance(message_chunk, AIMessageChunk):
            message_chunk.usage_metadata = usage_metadata

        generation_chunk = ChatGenerationChunk(
            message=message_chunk, generation_info=generation_info or None
        )
        return generation_chunk

    @override
    def invoke(
        self,
        input: LanguageModelInput,
        config: RunnableConfig | None = None,
        *,
        stop: list[str] | None = None,
        **kwargs: object,
    ) -> BaseMessage:
        config = ensure_config(config)
        chat_result = cast(
            ChatGeneration,
            self.generate_prompt(
                [self._convert_input(input)],
                stop=stop,
                callbacks=config.get("callbacks"),
                tags=config.get("tags"),
                metadata=config.get("metadata"),
                run_name=config.get("run_name"),
                run_id=config.pop("run_id", None),
                **kwargs,
            ).generations[0][0],
        ).message

        response_metadata = _as_object_dict(cast(object, chat_result.response_metadata))
        token_usage = (
            response_metadata.get("token_usage") if response_metadata else None
        )
        token_usage_dict = _as_object_dict(token_usage)
        if token_usage_dict is not None:
            self.usage_metadata = token_usage_dict
        elif (
            isinstance(chat_result, AIMessage)
            and chat_result.usage_metadata is not None
        ):
            self.usage_metadata = dict(chat_result.usage_metadata)
        else:
            self.usage_metadata = {}
        return chat_result
