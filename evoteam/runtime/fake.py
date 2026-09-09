"""明确标记的无模型脚本 Runtime，只回传预置产物，不生成项目计划。"""

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import uuid4

from pydantic import JsonValue

from evoteam.domain.agent import AgentConfig, AgentMessage, AgentResult
from evoteam.domain.common import AssetRef
from evoteam.domain.role import RoleType
from evoteam.runtime.protocol import RuntimeAgent, RuntimeContext


@dataclass(frozen=True)
class ScriptedOutput:
    schema: AssetRef
    payload: dict[str, JsonValue]


class FakeRuntime:
    def __init__(self, outputs: Mapping[RoleType, ScriptedOutput]) -> None:
        self.outputs = dict(outputs)
        self._agents: dict[str, AgentConfig] = {}

    async def create_agent(self, config: AgentConfig, *, run_id: str) -> RuntimeAgent:
        if config.model_ref != AssetRef(id="fake", version="1"):
            raise ValueError("FakeRuntime 只接受 fake@1，不能冒充真实模型")
        if config.role not in self.outputs:
            raise ValueError("缺少角色的脚本产物")
        handle = RuntimeAgent(handle_id=str(uuid4()), run_id=run_id, node_id=config.node_id)
        self._agents[handle.handle_id] = config
        return handle

    async def invoke(
        self, agent: RuntimeAgent, message: AgentMessage, context: RuntimeContext
    ) -> AgentResult:
        if agent.run_id != context.run_id or agent.node_id != message.recipient_node_id:
            raise ValueError("FakeRuntime 输入身份不匹配")
        config = self._agents[agent.handle_id]
        output = self.outputs[config.role]
        # 没有模型调用，所以 Token 为 0；演示结果不能用于质量/成本实验。
        return AgentResult(
            instance_id=agent.handle_id,
            output_schema=output.schema,
            output=output.payload,
            input_tokens=0,
            output_tokens=0,
        ).model_copy(deep=True)

    async def close(self, agent: RuntimeAgent) -> None:
        del self._agents[agent.handle_id]
