"""Class for interacting with OpenAI through Chat APIs."""
import datetime
import logging
from typing import Callable, Generator, Optional, Type, TypeVar, Union
from warnings import warn

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from ...prompts import Prompt
from ..tools import OpenAITool
from ..types import OpenAIChatCompletion, OpenAIChatCompletionChunk
from ..utils import (
    convert_base_model_to_openai_tool,
    convert_tools_list_to_openai_tools,
    patch_openai_kwargs,
)

logger = logging.getLogger("mirascope")
BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class OpenAIChat:
    '''A convenience wrapper for the OpenAI Chat client.

    The Mirascope convenience wrapper for OpenAI provides a more user-friendly interface
    for interacting with their API. For detailed usage examples, check out the cookbook.

    Example:

    ```python
    import os

    from mirascope import OpenAIChat, Prompt

    os.environ["OPENAI_API_KEY"] = "YOUR_API_KEY"


    class BookRecommendationPrompt(Prompt):
        """
        Can you recommend some books on {topic}?
        """

        topic: str


    prompt = BookRecommendationPrompt(topic="how to bake a cake")
    model = OpenAIChat()
    res = model.create(prompt)

    print(str(res))
    #> Certinly! Here are some books on how to bake a cake:
    #  1. "The Cake Bible" by Rose Levy Beranbaum
    #  2. "Joy of Baking" by Irma S Rombauer and Marion Rombauer Becker
    #  ...
    ```

    '''

    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        """Initializes an instance of `OpenAIChat."""
        self.client = OpenAI(api_key=api_key, base_url=base_url, **kwargs)
        self.model = model

    def create(
        self,
        prompt: Optional[Union[Prompt, str]] = None,
        tools: Optional[list[Union[Callable, Type[OpenAITool]]]] = None,
        **kwargs,
    ) -> OpenAIChatCompletion:
        """Makes a call to the model using `prompt`.

        Args:
            prompt: The prompt to use for the call. This can either be a `Prompt`
                instance, a raw string, or `None`. If `prompt` is a `Prompt` instance,
                then the call will use the `CallParams` in the prompt before anything
                else. If `prompt` is `None`, then the call will attempt to use the
                `messages` keyword argument.
            tools: (Deprecated) A list of `OpenAITool` types or `Callable` functions
                that the creation call can decide to use. If `tools` is provided,
                `tool_choice` will be set to `auto` unless manually specified.
            **kwargs: Additional keyword arguments to pass to the API call. You can
                find available keyword arguments here:
                https://platform.openai.com/docs/api-reference/chat/create

        Returns:
            A `OpenAIChatCompletion` instance.

        Raises:
            ValueError: if neither `prompt` nor `messages` are provided.
            OpenAIError: raises any OpenAI errors, see:
                https://platform.openai.com/docs/guides/error-codes/api-errors
        """
        if tools is not None:
            warn(
                "The `tools` parameter is deprecated; version>=0.3.0. "
                "Use `CallParams` inside of your `Prompt` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        if isinstance(prompt, Prompt):
            if self.model != "gpt-3.5-turbo":
                warn(
                    "The `model` parameter will be ignored when `prompt` is of type "
                    "`Prompt` in favor of `CallParams.model` field inside of `prompt`; "
                    "version>=0.3.0. Use `CallParams` inside of your `Prompt` instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
            self.model = prompt._call_params.model
            if prompt._call_params.tools is not None:
                tools = prompt._call_params.tools

        start_time = datetime.datetime.now().timestamp() * 1000
        openai_tools = convert_tools_list_to_openai_tools(tools)
        patch_openai_kwargs(kwargs, prompt, openai_tools)
        completion = OpenAIChatCompletion(
            completion=self.client.chat.completions.create(
                model=self.model,
                stream=False,
                **kwargs,
            ),
            tool_types=openai_tools if tools else None,
        )
        completion._start_time = start_time
        completion._end_time = datetime.datetime.now().timestamp() * 1000
        return completion

    def stream(
        self,
        prompt: Optional[Union[Prompt, str]] = None,
        tools: Optional[list[Union[Callable, Type[OpenAITool]]]] = None,
        **kwargs,
    ) -> Generator[OpenAIChatCompletionChunk, None, None]:
        """Streams the response for a call to the model using `prompt`.

        Args:
            prompt: The `Prompt` to use for the call.
            tools: A list of `OpenAITool` types or `Callable` functions that the
                creation call can decide to use. If `tools` is provided, `tool_choice`
                will be set to `auto` unless manually specified.
            **kwargs: Additional keyword arguments to pass to the API call. You can
                find available keyword arguments here:
                https://platform.openai.com/docs/api-reference/chat/create

        Yields:
            A `OpenAIChatCompletionChunk` for each chunk of the response.

        Raises:
            ValueError: if neither `prompt` nor `messages` are provided.
            OpenAIError: raises any OpenAI errors, see:
                https://platform.openai.com/docs/guides/error-codes/api-errors
        """
        if tools is not None:
            warn(
                "The `tools` parameter is deprecated; version>=0.3.0. "
                "Use `CallParams` inside of your `Prompt` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        if isinstance(prompt, Prompt):
            if self.model != "gpt-3.5-turbo":
                warn(
                    "The `model` parameter will be ignored when `prompt` is of type "
                    "`Prompt` in favor of `CallParams.model` field inside of `prompt`; "
                    "version>=0.3.0. Use `CallParams` inside of your `Prompt` instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
            self.model = prompt._call_params.model
            if prompt._call_params.tools is not None:
                tools = prompt._call_params.tools

        openai_tools = convert_tools_list_to_openai_tools(tools)
        patch_openai_kwargs(kwargs, prompt, openai_tools)

        completion_stream = self.client.chat.completions.create(
            model=self.model,
            stream=True,
            **kwargs,
        )

        for chunk in completion_stream:
            yield OpenAIChatCompletionChunk(
                chunk=chunk,
                tool_types=openai_tools if tools else None,
            )

    def extract(
        self,
        schema: Type[BaseModelT],
        prompt: Optional[Union[Prompt, str]] = None,
        retries: int = 0,
        **kwargs,
    ) -> BaseModelT:
        """Extracts the given schema from the response of a chat `create` call.

        The given schema is converted into an `OpenAITool`, complete with a description
        of the tool, all of the fields, and their types. This allows us to take
        advantage of OpenAI's tool/function calling functionality to extract information
        from a prompt according to the context provided by the `BaseModel` schema.

        Args:
            schema: The `BaseModel` schema to extract from the completion.
            prompt: The prompt from which the schema will be extracted. If `prompt` is
                a `Prompt` instance, then the call will use the `CallParams` in the
                prompt.
            retries: The maximum number of times to retry the query on validation error.
            **kwargs: Additional keyword arguments to pass to the API call. You can
                find available keyword arguments here:
                https://platform.openai.com/docs/api-reference/chat/create

        Returns:
            The `Schema` instance extracted from the completion.

        Raises:
            ValidationError: if the schema cannot be instantiated from the completion.
            OpenAIError: raises any OpenAI errors, see:
                https://platform.openai.com/docs/guides/error-codes/api-errors
        """
        tool = convert_base_model_to_openai_tool(schema)
        completion = self.create(
            prompt,
            tools=[tool],
            tool_choice={
                "type": "function",
                "function": {"name": tool.__name__},
            },
            **kwargs,
        )

        try:
            return schema(**completion.tool.model_dump())  # type: ignore
        except (AttributeError, ValidationError) as e:
            if retries > 0:
                logging.info(f"Retrying due to exception: {e}")
                # TODO: update this to include failure history once prompts can handle
                # chat history properly.
                return self.extract(schema, prompt, retries - 1)
            raise  # re-raise if we have no retries left
