from typing import Any, cast

import pytest

from evoteam.domain.agent import AgentMessage, AgentResult
from evoteam.domain.common import AssetRef
from evoteam.experiment import RequestLimitedRuntime
from evoteam.runtime.protocol import RuntimeAgent, RuntimeContext


class _Delegate:
    def __init__(self) -> None:
        self.calls = 0

    async def invoke(self, agent, message, context):
        self.calls += 1
        return AgentResult(
            instance_id="instance",
            output_schema=AssetRef(id="output", version="1"),
            output={},
        )


@pytest.mark.asyncio
async def test_request_limit_stops_before_unregistered_extra_call():
    delegate = _Delegate()
    runtime = RequestLimitedRuntime(cast(Any, delegate), maximum_requests=2)
    agent = RuntimeAgent(handle_id="handle", run_id="run", node_id="node")
    message = AgentMessage(
        message_id="message",
        recipient_node_id="node",
        schema_ref=AssetRef(id="input", version="1"),
    )
    context = RuntimeContext(run_id="run", task_id="task")

    await runtime.invoke(agent, message, context)
    await runtime.invoke(agent, message, context)
    with pytest.raises(RuntimeError, match="请求上限"):
        await runtime.invoke(agent, message, context)

    assert runtime.requests_used == 2
    assert delegate.calls == 2
