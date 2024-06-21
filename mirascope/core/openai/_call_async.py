"""This module contains the OpenAI `call_async_decorator` function."""

import datetime
import inspect
from functools import wraps
from typing import Awaitable, Callable, ParamSpec

from openai import AsyncOpenAI

from ..base import BaseTool
from ._utils import (
    openai_api_calculate_cost,
    setup_call,
)
from .call_params import OpenAICallParams
from .call_response import OpenAICallResponse
from .function_return import OpenAICallFunctionReturn

_P = ParamSpec("_P")


def call_async_decorator(
    fn: Callable[_P, Awaitable[OpenAICallFunctionReturn]],
    model: str,
    tools: list[type[BaseTool] | Callable] | None,
    call_params: OpenAICallParams,
) -> Callable[_P, Awaitable[OpenAICallResponse]]:
    @wraps(fn)
    async def inner_async(*args: _P.args, **kwargs: _P.kwargs) -> OpenAICallResponse:
        fn_args = inspect.signature(fn).bind(*args, **kwargs).arguments
        fn_return = await fn(*args, **kwargs)
        prompt_template, messages, tool_types, call_kwargs = setup_call(
            fn, fn_args, fn_return, tools, call_params
        )
        client = AsyncOpenAI()
        start_time = datetime.datetime.now().timestamp() * 1000
        response = await client.chat.completions.create(
            model=model, stream=False, messages=messages, **call_kwargs
        )
        return OpenAICallResponse(
            response=response,
            tool_types=tool_types,
            prompt_template=prompt_template,
            fn_args=fn_args,
            fn_return=fn_return,
            messages=messages,
            call_params=call_kwargs,
            user_message_param=messages[-1] if messages[-1]["role"] == "user" else None,
            start_time=start_time,
            end_time=datetime.datetime.now().timestamp() * 1000,
            cost=openai_api_calculate_cost(response.usage, response.model),
        )

    return inner_async
