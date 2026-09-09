"""Runtime 的框架无关端口；SDK 对象不得出现在公共签名中。"""

from dataclasses import dataclass
from typing import Protocol

from evoteam.domain.agent import AgentConfig, AgentMessage, AgentResult
from evoteam.domain.common import FrozenModel, Identifier, RunBudget
from evoteam.domain.events import TraceEvent


@dataclass(frozen=True)
class RuntimeAgent:
    """不透明运行句柄，SDK 对象由 Adapter 内部管理。"""

    handle_id: str
    run_id: str
    node_id: str


class RuntimeContext(FrozenModel):
    run_id: Identifier
    task_id: Identifier
    budget: RunBudget = RunBudget()
    source_event_ids: tuple[str, ...] = ()


class EventSink(Protocol):
    async def emit(self, event: TraceEvent) -> None: ...


class AgentRuntime(Protocol):
    async def create_agent(self, config: AgentConfig, *, run_id: str) -> RuntimeAgent: ...
    async def invoke(
        self,
        agent: RuntimeAgent,
        message: AgentMessage,
        context: RuntimeContext,
    ) -> AgentResult: ...
    async def close(self, agent: RuntimeAgent) -> None: ...
