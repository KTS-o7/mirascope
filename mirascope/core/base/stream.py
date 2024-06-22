"""This module contains the base classes for streaming responses from LLMs."""

from abc import ABC
from collections.abc import Generator
from typing import Callable, Generic, TypeVar

from .call_response_chunk import BaseCallResponseChunk
from .tool import BaseTool

_BaseCallResponseChunkT = TypeVar(
    "_BaseCallResponseChunkT", bound=BaseCallResponseChunk
)
_UserMessageParamT = TypeVar("_UserMessageParamT")
_AssistantMessageParamT = TypeVar("_AssistantMessageParamT")
_BaseToolT = TypeVar("_BaseToolT", bound=BaseTool)
_OutputT = TypeVar("_OutputT")


class BaseStream(
    Generic[
        _BaseCallResponseChunkT,
        _UserMessageParamT,
        _AssistantMessageParamT,
        _BaseToolT,
        _OutputT,
    ],
    ABC,
):
    """A base class for streaming responses from LLMs."""

    stream: Generator[_BaseCallResponseChunkT, None, None]
    message_param_type: type[_AssistantMessageParamT]
    output_parser: Callable[[_BaseCallResponseChunkT], _OutputT] | None

    cost: float | None = None
    user_message_param: _UserMessageParamT | None = None
    message_param: _AssistantMessageParamT

    def __init__(
        self,
        stream: Generator[_BaseCallResponseChunkT, None, None],
        message_param_type: type[_AssistantMessageParamT],
        output_parser: Callable[[_BaseCallResponseChunkT], _OutputT] | None = None,
    ):
        """Initializes an instance of `BaseStream`."""
        self.stream = stream
        self.message_param_type = message_param_type
        self.output_parser = output_parser

    def __iter__(
        self,
    ) -> Generator[
        tuple[_BaseCallResponseChunkT | _OutputT, _BaseToolT | None], None, None
    ]:
        """Iterator over the stream and stores useful information."""
        content = ""
        for chunk in self.stream:
            self.user_message_param = chunk.user_message_param
            content += chunk.content
            if chunk.cost is not None:
                self.cost = chunk.cost
            if self.output_parser is not None:
                chunk = self.output_parser(chunk)
            yield chunk, None
        kwargs = {"role": "assistant"}
        if "message" in self.message_param_type.__annotations__:
            kwargs["message"] = content
        else:
            kwargs["content"] = content
        self.message_param = self.message_param_type(**kwargs)
