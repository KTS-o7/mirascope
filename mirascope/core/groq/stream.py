"""The `GroqStream` class for convenience around streaming LLM calls."""

from groq.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)
from groq.types.chat.chat_completion import Choice
from groq.types.chat.chat_completion_message import ChatCompletionMessage

from ..base._stream import BaseStream
from ._utils import calculate_cost
from .call_params import GroqCallParams
from .call_response import GroqCallResponse
from .call_response_chunk import GroqCallResponseChunk
from .dynamic_config import GroqDynamicConfig
from .tool import GroqTool


class GroqStream(
    BaseStream[
        GroqCallResponse,
        GroqCallResponseChunk,
        ChatCompletionUserMessageParam,
        ChatCompletionAssistantMessageParam,
        ChatCompletionToolMessageParam,
        ChatCompletionMessageParam,
        GroqTool,
        GroqDynamicConfig,
        GroqCallParams,
    ]
):
    _provider = "groq"

    @property
    def cost(self) -> float | None:
        """Returns the cost of the call."""
        return calculate_cost(self.input_tokens, self.output_tokens, self.model)

    def _construct_message_param(
        self,
        tool_calls: list[ChatCompletionMessageToolCallParam] | None = None,
        content: str | None = None,
    ) -> ChatCompletionAssistantMessageParam:
        message_param = ChatCompletionAssistantMessageParam(
            role="assistant",
            content=content,
        )
        if tool_calls:
            message_param["tool_calls"] = tool_calls
        return message_param

    def construct_call_response(self) -> GroqCallResponse:
        """Constructs the call response from a consumed GroqStream."""
        if self.message_param is None:
            raise ValueError(  # pragma: no cover
                "No stream response, check if the stream has been consumed."
            )
        message = {
            "role": self.message_param["role"],
            "content": self.message_param.get("content", ""),
            "tool_calls": self.message_param.get("tool_calls", []),
        }
        completion = ChatCompletion(
            id=self.id if self.id else "",
            model=self.model,
            choices=[
                Choice(
                    finish_reason=self.finish_reasons[0]
                    if self.finish_reasons and self.finish_reasons[0]
                    else "stop",  # type: ignore
                    index=0,
                    message=ChatCompletionMessage.model_validate(message),
                )
            ],
            created=0,
            object="chat.completion",
        )
        return GroqCallResponse(
            metadata=self.metadata,
            response=completion,
            tool_types=self.tool_types,
            prompt_template=self.prompt_template,
            fn_args=self.fn_args if self.fn_args else {},
            dynamic_config=self.dynamic_config,
            messages=self.messages,
            call_params=self.call_params,
            call_kwargs=self.call_kwargs,
            user_message_param=self.user_message_param,
            start_time=self.start_time,
            end_time=self.end_time,
        )
