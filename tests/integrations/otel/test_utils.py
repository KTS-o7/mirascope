import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from mirascope.core.base._stream import BaseStream
from mirascope.core.base._structured_stream import BaseStructuredStream
from mirascope.core.base.call_response import BaseCallResponse
from mirascope.core.base.tool import BaseTool
from mirascope.integrations.otel import _utils


class FormatBook(BaseTool):
    """Returns the title and author of a book nicely formatted."""

    title: str = Field(..., description="The title of the book.")
    author: str = Field(..., description="The author of the book in all caps.")

    def call(self) -> str:
        return f"{self.title} by {self.author}"  # pragma: no cover


class MyCallResponse(BaseCallResponse):
    @property
    def content(self) -> str:
        return "content"  # pragma: no cover

    @property
    def tools(self) -> list[BaseTool]:
        return [
            FormatBook(title="The Name of the Wind", author="Rothfuss, Patrick")
        ]  # pragma: no cover


patch.multiple(MyCallResponse, __abstractmethods__=set()).start()
patch.multiple(BaseStream, __abstractmethods__=set()).start()


class MyStream(BaseStream):
    _provider = "test"

    @property
    def cost(self):
        return 10  # pragma: no cover


@patch("mirascope.integrations.otel._utils.get_tracer", new_callable=MagicMock)
def test_custom_context_manager(mock_get_tracer: MagicMock):
    # Create a mock span and set the return value for the tracer's method
    mock_fn = MagicMock(__name__="dummy_function")
    mock_span = MagicMock(name="MockSpan")
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value = mock_span
    mock_span.__enter__.return_value = mock_span
    mock_get_tracer.return_value = mock_tracer

    # Use the context manager and assert the span is yielded
    with _utils.custom_context_manager(mock_fn) as span:
        mock_get_tracer.assert_called_once_with("otel")
        assert span is mock_span
        mock_tracer.start_as_current_span.assert_called_once_with("dummy_function")


@patch("mirascope.integrations.otel._utils.get_tracer", new_callable=MagicMock)
@patch("mirascope.integrations.otel._utils.set_tracer_provider", new_callable=MagicMock)
@patch("mirascope.integrations.otel._utils.TracerProvider", new_callable=MagicMock)
@patch("mirascope.integrations.otel._utils.SimpleSpanProcessor", new_callable=MagicMock)
@patch("mirascope.integrations.otel._utils.ConsoleSpanExporter", new_callable=MagicMock)
def test_configure_no_processor(
    mock_console_span_exporter: MagicMock,
    mock_simple_span_processor: MagicMock,
    mock_tracer_provider: MagicMock,
    mock_set_tracer_provider: MagicMock,
    mock_get_tracer: MagicMock,
):
    mock_add_span_processor = MagicMock()
    mock_tracer_provider.return_value.add_span_processor = mock_add_span_processor
    _utils.configure(None)
    mock_tracer_provider.assert_called_once()
    mock_console_span_exporter.assert_called_once()
    mock_simple_span_processor.assert_called_once_with(
        mock_console_span_exporter.return_value
    )
    mock_add_span_processor.assert_called_once_with(
        mock_simple_span_processor.return_value
    )
    mock_set_tracer_provider.assert_called_once_with(mock_tracer_provider.return_value)
    mock_get_tracer.assert_called_once_with("otel")


@patch("mirascope.integrations.otel._utils.get_tracer", new_callable=MagicMock)
@patch("mirascope.integrations.otel._utils.set_tracer_provider", new_callable=MagicMock)
@patch("mirascope.integrations.otel._utils.TracerProvider", new_callable=MagicMock)
def test_configure_with_processors(
    mock_tracer_provider: MagicMock,
    mock_set_tracer_provider: MagicMock,
    mock_get_tracer: MagicMock,
):
    processors: list = [MagicMock()]
    mock_add_span_processor = MagicMock()
    mock_tracer_provider.return_value.add_span_processor = mock_add_span_processor
    _utils.configure(processors)
    mock_tracer_provider.assert_called_once()
    mock_add_span_processor.assert_called_once_with(processors[0])
    mock_set_tracer_provider.assert_called_once_with(mock_tracer_provider.return_value)
    mock_get_tracer.assert_called_once_with("otel")


def test_get_call_response_attributes():
    call_response = MyCallResponse(
        metadata={"tags": {"version:0001"}},
        response="hello world",
        tool_types=[],
        prompt_template="Recommend a {genre} book for me to read.",
        fn_args={"genre": "nonfiction"},
        dynamic_config={"computed_fields": {"genre": "nonfiction"}},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Recommend a nonfiction book for me to read.",
                    }
                ],
            }
        ],
        call_params={"tool_choice": "required"},
        call_kwargs={
            "tool_choice": "required",
            "tools": [
                {
                    "function": {
                        "name": "FormatBook",
                        "description": "Returns the title and author of a book nicely formatted.",
                        "parameters": {
                            "$defs": {
                                "ChatCompletionMessageToolCall": {
                                    "additionalProperties": True,
                                    "properties": {
                                        "id": {"title": "Id", "type": "string"},
                                        "function": {"$ref": "#/$defs/Function"},
                                        "type": {
                                            "const": "function",
                                            "enum": ["function"],
                                            "title": "Type",
                                            "type": "string",
                                        },
                                    },
                                    "required": ["id", "function", "type"],
                                    "title": "ChatCompletionMessageToolCall",
                                    "type": "object",
                                },
                                "Function": {
                                    "additionalProperties": True,
                                    "properties": {
                                        "arguments": {
                                            "title": "Arguments",
                                            "type": "string",
                                        },
                                        "name": {"title": "Name", "type": "string"},
                                    },
                                    "required": ["arguments", "name"],
                                    "title": "Function",
                                    "type": "object",
                                },
                            },
                            "properties": {
                                "tool_call": {
                                    "$ref": "#/$defs/ChatCompletionMessageToolCall"
                                },
                                "title": {
                                    "examples": ["The Name of the Wind"],
                                    "title": "Title",
                                    "type": "string",
                                },
                                "author": {
                                    "examples": ["Rothfuss, Patrick"],
                                    "title": "Author",
                                    "type": "string",
                                },
                            },
                            "required": ["tool_call", "title", "author"],
                            "type": "object",
                        },
                    },
                    "type": "function",
                }
            ],
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Recommend a nonfiction book for me to read.",
                        }
                    ],
                }
            ],
        },
        user_message_param={
            "role": "user",
            "content": [
                {"type": "text", "text": "Recommend a nonfiction book for me to read."}
            ],
        },
        start_time=100,
        end_time=200,
    )  # type: ignore
    result = _utils.get_call_response_attributes(call_response)
    assert result["gen_ai.system"] == call_response.prompt_template
    assert result["gen_ai.request.model"] == call_response.call_kwargs.get("model")
    assert result["gen_ai.request.max_tokens"] == 0
    assert result["gen_ai.request.temperature"] == 0
    assert result["gen_ai.request.top_p"] == 0
    assert result["gen_ai.response.model"] == (
        call_response.model if call_response.model else ""
    )
    assert result["gen_ai.response.id"] == (
        call_response.id if call_response.id else ""
    )
    assert result["gen_ai.response.finish_reasons"] == (
        call_response.finish_reasons if call_response.finish_reasons else ""
    )
    assert result["gen_ai.usage.completion_tokens"] == (
        call_response.output_tokens if call_response.output_tokens else ""
    )
    assert result["gen_ai.usage.prompt_tokens"] == (
        call_response.input_tokens if call_response.input_tokens else ""
    )


def test_set_call_response_event_attributes():
    result = MagicMock()
    result.user_message_param = {"role": "user", "content": "user_content"}
    result.message_param = {"role": "assistant", "content": "assistant_content"}
    span = MagicMock()
    add_event = MagicMock()
    span.add_event = add_event

    _utils.set_call_response_event_attributes(result, span)
    assert add_event.call_count == 2
    assert add_event.call_args_list[0][0][0] == "gen_ai.content.prompt"
    assert add_event.call_args_list[0][1]["attributes"]["gen_ai.prompt"] == json.dumps(
        result.user_message_param
    )
    assert add_event.call_args_list[1][0][0] == "gen_ai.content.completion"
    assert add_event.call_args_list[1][1]["attributes"][
        "gen_ai.completion"
    ] == json.dumps(result.message_param)


def test_set_stream_event_attributes():
    result = MagicMock()
    result.user_message_param = {"role": "user", "content": "user_content"}
    result.message_param = {"role": "assistant", "content": "assistant_content"}
    span = MagicMock()
    add_event = MagicMock()
    span.add_event = add_event

    _utils.set_stream_event_attributes(result, span)
    assert add_event.call_count == 2
    assert add_event.call_args_list[0][0][0] == "gen_ai.content.prompt"
    assert add_event.call_args_list[0][1]["attributes"]["gen_ai.prompt"] == json.dumps(
        result.user_message_param
    )
    assert add_event.call_args_list[1][0][0] == "gen_ai.content.completion"
    assert add_event.call_args_list[1][1]["attributes"][
        "gen_ai.completion"
    ] == json.dumps(result.message_param)


def test_get_stream_attributes():
    stream = MagicMock()
    stream.prompt_template = "Recommend a {genre} book for me to read."
    stream.model = "foo-123"
    stream.call_params = {
        "max_tokens": 1,
        "temperature": 1,
        "top_p": 1,
    }
    stream.call_kwargs = {
        "model": "foo",
    }
    stream.output_tokens = 1
    stream.input_tokens = 1

    result = _utils.get_stream_attributes(stream)
    assert result["gen_ai.system"] == stream.prompt_template
    assert result["gen_ai.request.model"] == stream.call_kwargs.get("model")
    assert result["gen_ai.request.max_tokens"] == 0
    assert result["gen_ai.request.temperature"] == 0
    assert result["gen_ai.request.top_p"] == 0
    assert result["gen_ai.response.model"] == stream.model
    assert result["gen_ai.usage.completion_tokens"] == stream.output_tokens
    assert result["gen_ai.usage.prompt_tokens"] == stream.input_tokens


@patch(
    "mirascope.integrations.otel._utils.get_call_response_attributes",
    new_callable=MagicMock,
    return_value={},
)
@patch(
    "mirascope.integrations.otel._utils.set_call_response_event_attributes",
    new_callable=MagicMock,
    return_value={},
)
def test_handle_call_response(
    mock_set_call_response_event_attributes: MagicMock,
    mock_get_call_response_attributes: MagicMock,
):
    mock_fn = MagicMock()
    assert _utils.handle_call_response(MagicMock(), mock_fn, None) is None

    result = MagicMock()
    result.tools = [
        FormatBook(title="The Name of the Wind", author="Rothfuss, Patrick")
    ]
    span = MagicMock()
    set_attributes = MagicMock()
    span.set_attributes = set_attributes
    _utils.handle_call_response(result, mock_fn, span)
    assert set_attributes.call_count == 1
    mock_get_call_response_attributes.assert_called_once_with(result)
    assert mock_get_call_response_attributes.return_value["async"] is False
    mock_set_call_response_event_attributes.assert_called_once_with(result, span)


@patch(
    "mirascope.integrations.otel._utils.get_call_response_attributes",
    new_callable=MagicMock,
    return_value={},
)
@patch(
    "mirascope.integrations.otel._utils.set_call_response_event_attributes",
    new_callable=MagicMock,
    return_value={},
)
@pytest.mark.asyncio
async def test_handle_call_response_async(
    mock_set_call_response_event_attributes: MagicMock,
    mock_get_call_response_attributes: MagicMock,
):
    mock_fn = MagicMock()
    assert await _utils.handle_call_response_async(MagicMock(), mock_fn, None) is None

    result = MagicMock()
    result.tools = [
        FormatBook(title="The Name of the Wind", author="Rothfuss, Patrick")
    ]
    span = MagicMock()
    set_attributes = MagicMock()
    span.set_attributes = set_attributes
    await _utils.handle_call_response_async(result, mock_fn, span)
    assert set_attributes.call_count == 1
    mock_get_call_response_attributes.assert_called_once_with(result)
    assert mock_get_call_response_attributes.return_value["async"] is True
    mock_set_call_response_event_attributes.assert_called_once_with(result, span)


@patch(
    "mirascope.integrations.otel._utils.get_stream_attributes",
    new_callable=MagicMock,
    return_value={},
)
@patch(
    "mirascope.integrations.otel._utils.set_stream_event_attributes",
    new_callable=MagicMock,
    return_value={},
)
def test_handle_stream(
    mock_set_stream_event_attributes: MagicMock,
    mock_get_stream_attributes: MagicMock,
):
    mock_fn = MagicMock()
    assert _utils.handle_stream(MagicMock(), mock_fn, None) is None

    result = MagicMock()
    span = MagicMock()
    set_attributes = MagicMock()
    span.set_attributes = set_attributes
    _utils.handle_stream(result, mock_fn, span)
    assert set_attributes.call_count == 1
    mock_get_stream_attributes.assert_called_once_with(result)
    assert mock_get_stream_attributes.return_value["async"] is False
    mock_set_stream_event_attributes.assert_called_once_with(result, span)


@patch(
    "mirascope.integrations.otel._utils.get_stream_attributes",
    new_callable=MagicMock,
    return_value={},
)
@patch(
    "mirascope.integrations.otel._utils.set_stream_event_attributes",
    new_callable=MagicMock,
    return_value={},
)
@pytest.mark.asyncio
async def test_handle_stream_async(
    mock_set_stream_event_attributes: MagicMock,
    mock_get_stream_attributes: MagicMock,
):
    mock_fn = MagicMock()
    assert await _utils.handle_stream_async(MagicMock(), mock_fn, None) is None

    result = MagicMock()
    span = MagicMock()
    set_attributes = MagicMock()
    span.set_attributes = set_attributes
    await _utils.handle_stream_async(result, mock_fn, span)
    assert set_attributes.call_count == 1
    mock_get_stream_attributes.assert_called_once_with(result)
    assert mock_get_stream_attributes.return_value["async"] is True
    mock_set_stream_event_attributes.assert_called_once_with(result, span)


@patch(
    "mirascope.integrations.otel._utils.get_call_response_attributes",
    new_callable=MagicMock,
    return_value={},
)
def test_handle_base_model(
    mock_get_call_response_attributes: MagicMock,
):
    mock_fn = MagicMock()
    assert _utils.handle_base_model(MagicMock(), mock_fn, None) is None

    result = MagicMock(spec=BaseModel)
    response = MagicMock()
    result._response = response
    response.user_message_param = {"role": "user", "content": "user_content"}
    span = MagicMock()
    add_event = MagicMock()
    span.add_event = add_event
    set_attributes = MagicMock()
    span.set_attributes = set_attributes
    _utils.handle_base_model(result, mock_fn, span)
    assert set_attributes.call_count == 1
    mock_get_call_response_attributes.assert_called_once_with(response)
    assert mock_get_call_response_attributes.return_value["async"] is False

    assert add_event.call_count == 2
    assert add_event.call_args_list[0][0][0] == "gen_ai.content.prompt"
    assert add_event.call_args_list[0][1]["attributes"]["gen_ai.prompt"] == json.dumps(
        response.user_message_param
    )
    assert add_event.call_args_list[1][0][0] == "gen_ai.content.completion"
    assert (
        add_event.call_args_list[1][1]["attributes"]["gen_ai.completion"]
        == result.model_dump_json()
    )


@patch(
    "mirascope.integrations.otel._utils.get_stream_attributes",
    new_callable=MagicMock,
    return_value={},
)
def test_handle_structured_stream(
    mock_get_stream_attributes: MagicMock,
):
    mock_fn = MagicMock()
    assert _utils.handle_structured_stream(MagicMock(), mock_fn, None) is None

    class Foo(BaseModel):
        bar: str

    result = MagicMock(spec=BaseStructuredStream)
    response = MagicMock()
    result.stream = response
    result.constructed_response_model = Foo(bar="baz")
    response.user_message_param = {"role": "user", "content": "user_content"}
    span = MagicMock()
    add_event = MagicMock()
    span.add_event = add_event
    set_attributes = MagicMock()
    span.set_attributes = set_attributes
    _utils.handle_structured_stream(result, mock_fn, span)
    assert set_attributes.call_count == 1
    mock_get_stream_attributes.assert_called_once_with(response)
    assert mock_get_stream_attributes.return_value["async"] is False

    assert add_event.call_count == 2
    assert add_event.call_args_list[0][0][0] == "gen_ai.content.prompt"
    assert add_event.call_args_list[0][1]["attributes"]["gen_ai.prompt"] == json.dumps(
        response.user_message_param
    )
    assert add_event.call_args_list[1][0][0] == "gen_ai.content.completion"
    assert (
        add_event.call_args_list[1][1]["attributes"]["gen_ai.completion"]
        == Foo(bar="baz").model_dump_json()
    )
    result.constructed_response_model = "test"
    _utils.handle_structured_stream(result, mock_fn, span)
    assert add_event.call_args_list[3][1]["attributes"]["gen_ai.completion"] == "test"


@patch(
    "mirascope.integrations.otel._utils.get_call_response_attributes",
    new_callable=MagicMock,
    return_value={},
)
@pytest.mark.asyncio
async def test_handle_base_model_async(
    mock_get_call_response_attributes: MagicMock,
):
    mock_fn = MagicMock()
    assert await _utils.handle_base_model_async(MagicMock(), mock_fn, None) is None

    result = MagicMock(spec=BaseModel)
    response = MagicMock()
    result._response = response
    response.user_message_param = {"role": "user", "content": "user_content"}
    span = MagicMock()
    add_event = MagicMock()
    span.add_event = add_event
    set_attributes = MagicMock()
    span.set_attributes = set_attributes
    await _utils.handle_base_model_async(result, mock_fn, span)
    assert set_attributes.call_count == 1
    mock_get_call_response_attributes.assert_called_once_with(response)
    assert mock_get_call_response_attributes.return_value["async"] is True

    assert add_event.call_count == 2
    assert add_event.call_args_list[0][0][0] == "gen_ai.content.prompt"
    assert add_event.call_args_list[0][1]["attributes"]["gen_ai.prompt"] == json.dumps(
        response.user_message_param
    )
    assert add_event.call_args_list[1][0][0] == "gen_ai.content.completion"
    assert (
        add_event.call_args_list[1][1]["attributes"]["gen_ai.completion"]
        == result.model_dump_json()
    )


@patch(
    "mirascope.integrations.otel._utils.get_stream_attributes",
    new_callable=MagicMock,
    return_value={},
)
@pytest.mark.asyncio
async def test_handle_structured_stream_async(
    mock_get_stream_attributes: MagicMock,
):
    mock_fn = MagicMock()
    assert (
        await _utils.handle_structured_stream_async(MagicMock(), mock_fn, None) is None
    )

    class Foo(BaseModel):
        bar: str

    result = MagicMock(spec=BaseStructuredStream)
    response = MagicMock()
    result.stream = response
    result.constructed_response_model = Foo(bar="baz")
    response.user_message_param = {"role": "user", "content": "user_content"}
    span = MagicMock()
    add_event = MagicMock()
    span.add_event = add_event
    set_attributes = MagicMock()
    span.set_attributes = set_attributes
    await _utils.handle_structured_stream_async(result, mock_fn, span)
    assert set_attributes.call_count == 1
    mock_get_stream_attributes.assert_called_once_with(response)
    assert mock_get_stream_attributes.return_value["async"] is True

    assert add_event.call_count == 2
    assert add_event.call_args_list[0][0][0] == "gen_ai.content.prompt"
    assert add_event.call_args_list[0][1]["attributes"]["gen_ai.prompt"] == json.dumps(
        response.user_message_param
    )
    assert add_event.call_args_list[1][0][0] == "gen_ai.content.completion"
    assert (
        add_event.call_args_list[1][1]["attributes"]["gen_ai.completion"]
        == Foo(bar="baz").model_dump_json()
    )
    result.constructed_response_model = "test"
    await _utils.handle_structured_stream_async(result, mock_fn, span)
    assert add_event.call_args_list[3][1]["attributes"]["gen_ai.completion"] == "test"
