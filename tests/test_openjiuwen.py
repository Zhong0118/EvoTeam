"""真实 openJiuwen SDK 接本地 HTTP 服务；不以 Mock SDK 冒充集成验证。"""

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic import SecretStr

from evoteam.bootstrap import build_v0_strategy
from evoteam.domain.agent import AgentMessage
from evoteam.domain.common import AssetRef, RunBudget
from evoteam.domain.planning import AGENT_INPUT_SCHEMA, ANALYSIS_SCHEMA
from evoteam.runtime.openjiuwen.adapter import OpenJiuwenRuntimeAdapter
from evoteam.runtime.protocol import RuntimeContext


@contextmanager
def completion_server(
    *,
    content=None,
    status=200,
    usage: bool | dict[str, int] = True,
    finish_reason="stop",
    delay: float = 0,
):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(payload)
            if delay:
                import time

                time.sleep(delay)
            body = {
                "id": "local-completion",
                "object": "chat.completion",
                "created": 0,
                "model": "fixture-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": finish_reason,
                        "message": {
                            "role": "assistant",
                            "content": (content(len(requests)) if callable(content) else content)
                            or '{"summary":"按依赖执行","constraint_refs":[]}',
                        },
                    }
                ],
            }
            if usage:
                body["usage"] = (
                    usage
                    if isinstance(usage, dict)
                    else {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
                )
            encoded = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def endpoint(url):
    from evoteam.runtime.models import ModelEndpoint

    return ModelEndpoint(
        ref=AssetRef(id="fixture", version="1"),
        model_name="fixture-model",
        base_url=url,
        api_key=SecretStr("local-test-key"),
        timeout_seconds=5,
        max_output_tokens=40,
        temperature=0,
        top_p=1,
    )


def message(node_id="planner"):
    return AgentMessage(
        message_id="message",
        recipient_node_id=node_id,
        schema_ref=AGENT_INPUT_SCHEMA,
        payload={"task": {"instruction": "规划"}, "upstream": {}},
    )


def context():
    return RuntimeContext(
        run_id="run-1",
        task_id="task-1",
        budget=RunBudget(max_tokens=30, max_tool_calls=0, timeout_seconds=5),
    )


@pytest.mark.asyncio
async def test_real_sdk_sends_prompt_json_contract_output_limit_and_reports_usage():
    with completion_server() as (url, requests):
        adapter = OpenJiuwenRuntimeAdapter(models=(endpoint(url),))
        config = build_v0_strategy(model_ref=AssetRef(id="fixture", version="1")).definition.agents[
            0
        ]
        handle = await adapter.create_agent(config, run_id="run-1")
        result = await adapter.invoke(handle, message(), context())
        assert result.output_schema == ANALYSIS_SCHEMA
        assert result.output["summary"] == "按依赖执行"
        assert (result.input_tokens, result.output_tokens) == (12, 8)
        assert len(requests) == 1
        assert requests[0]["max_tokens"] <= 30
        assert requests[0]["response_format"] == {"type": "json_object"}
        assert requests[0].get("tools") in (None, [])
        assert "constraint_refs" in requests[0]["messages"][0]["content"]
        await adapter.close(handle)
        with pytest.raises(ValueError):
            await adapter.invoke(handle, message(), context())


@pytest.mark.asyncio
async def test_http_failure_is_not_retried():
    with completion_server(status=500) as (url, requests):
        adapter = OpenJiuwenRuntimeAdapter(models=(endpoint(url),))
        config = build_v0_strategy(model_ref=AssetRef(id="fixture", version="1")).definition.agents[
            0
        ]
        handle = await adapter.create_agent(config, run_id="run-1")
        with pytest.raises(Exception):
            await adapter.invoke(handle, message(), context())
        assert len(requests) == 1
        await adapter.close(handle)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content,usage,finish",
    [
        ("not JSON", True, "stop"),
        ('{"summary":"partial","constraint_refs":[]}', True, "length"),
        ('{"summary":"ok","constraint_refs":[]}', False, "stop"),
    ],
)
async def test_invalid_or_partial_output_and_missing_usage_are_not_fabricated(
    content, usage, finish
):
    with completion_server(content=content, usage=usage, finish_reason=finish) as (url, _):
        adapter = OpenJiuwenRuntimeAdapter(models=(endpoint(url),))
        config = build_v0_strategy(model_ref=AssetRef(id="fixture", version="1")).definition.agents[
            0
        ]
        handle = await adapter.create_agent(config, run_id="run-1")
        result = await adapter.invoke(handle, message(), context())
        if not usage:
            assert result.input_tokens is None and result.output_tokens is None
        else:
            assert "raw_response" in result.output
        await adapter.close(handle)


@pytest.mark.parametrize(
    "url", ["https://user:password@example.com/v1", "https://example.com/v1?api_key=secret"]
)
def test_model_binding_rejects_credentials_embedded_in_url(url):
    with pytest.raises(ValueError):
        endpoint(url)


@pytest.mark.asyncio
async def test_partial_provider_usage_does_not_become_zero_cost():
    with completion_server(usage={"total_tokens": 20}) as (url, _):
        adapter = OpenJiuwenRuntimeAdapter(models=(endpoint(url),))
        config = build_v0_strategy(model_ref=AssetRef(id="fixture", version="1")).definition.agents[
            0
        ]
        handle = await adapter.create_agent(config, run_id="run-1")
        result = await adapter.invoke(handle, message(), context())
        assert result.input_tokens is None and result.output_tokens is None
        await adapter.close(handle)


@pytest.mark.asyncio
async def test_close_releases_sdk_checkpoint_as_well_as_local_handle():
    from openjiuwen.core.session.checkpointer.checkpointer import CheckpointerFactory

    with completion_server() as (url, _):
        adapter = OpenJiuwenRuntimeAdapter(models=(endpoint(url),))
        config = build_v0_strategy(model_ref=AssetRef(id="fixture", version="1")).definition.agents[
            0
        ]
        handle = await adapter.create_agent(config, run_id="run-1")
        await adapter.invoke(handle, message(), context())
        checkpointer = CheckpointerFactory.get_checkpointer()
        assert await checkpointer.session_exists(handle.handle_id)
        await adapter.close(handle)
        assert not await checkpointer.session_exists(handle.handle_id)
