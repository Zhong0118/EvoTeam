"""锁定 SDK 的 ReActAgent 适配：单次调用、零工具、独立上下文和真实用量。"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from evoteam.capabilities.prompts import load_prompt
from evoteam.domain.agent import AgentConfig, AgentMessage, AgentResult
from evoteam.domain.planning import (
    AGENT_INPUT_SCHEMA,
    ANALYSIS_SCHEMA,
    PLAN_SCHEMA,
    REVIEW_SCHEMA,
    PlanningAnalysis,
    PlanningReview,
    ProjectPlan,
)
from evoteam.domain.role import RoleType
from evoteam.runtime.models import ModelEndpoint
from evoteam.runtime.protocol import RuntimeAgent, RuntimeContext

MAX_REACT_ITERATIONS = 3


@dataclass
class _Session:
    handle: RuntimeAgent
    config: AgentConfig
    endpoint: ModelEndpoint
    agent: Any
    responses: list[Any] = field(default_factory=list)
    invoked: bool = False
    running: bool = False


class OpenJiuwenRuntimeAdapter:
    """SDK 对象只留在本层；每个句柄至多调用一次，避免隐藏对话历史。"""

    def __init__(self, *, models: tuple[ModelEndpoint, ...] = ()) -> None:
        self._models = {(m.ref.id, m.ref.version): m for m in models}
        if len(self._models) != len(models):
            raise ValueError("模型引用必须唯一")
        self._sessions: dict[str, _Session] = {}

    async def create_agent(self, config: AgentConfig, *, run_id: str) -> RuntimeAgent:
        endpoint = self._models.get((config.model_ref.id, config.model_ref.version))
        if endpoint is None:
            raise ValueError("未登记 openJiuwen 模型配置")
        if (
            config.tool_policy.allowed_tools
            or config.tool_policy.required_tools
            or config.skill_refs
            or config.runtime_config.max_retries
        ):
            raise ValueError("当前 Adapter 只支持无 Tool / Skill / Runtime Retry")
        if config.role not in {
            RoleType.PLANNER,
            RoleType.EXECUTOR,
            RoleType.VERIFIER,
            RoleType.CRITIC,
        }:
            raise ValueError("当前 Adapter 尚未登记该角色的输出 Schema")
        load_prompt(config.prompt_ref)
        # 延迟导入，普通包导入、配置预览和 Fake 测试不初始化 SDK。
        from openjiuwen.core.single_agent.agents.react_agent import ReActAgent
        from openjiuwen.core.single_agent.rail.base import AgentCallbackEvent
        from openjiuwen.core.single_agent.schema.agent_card import AgentCard

        handle = RuntimeAgent(handle_id=str(uuid4()), run_id=run_id, node_id=config.node_id)
        agent = ReActAgent(AgentCard(id=handle.handle_id, name=config.node_id))
        state = _Session(handle, config, endpoint, agent)

        async def capture_response(ctx):
            response = getattr(ctx.inputs, "response", None)
            if response is not None:
                state.responses.append(response)

        await agent.register_callback(AgentCallbackEvent.AFTER_MODEL_CALL, capture_response)
        self._sessions[handle.handle_id] = state
        return handle

    async def invoke(
        self, agent: RuntimeAgent, message: AgentMessage, context: RuntimeContext
    ) -> AgentResult:
        state = self._sessions.get(agent.handle_id)
        if state is None or state.handle != agent or state.invoked:
            raise ValueError("未知、已关闭或已使用的 Runtime 句柄")
        if (
            context.run_id != agent.run_id
            or message.recipient_node_id != agent.node_id
            or message.schema_ref != AGENT_INPUT_SCHEMA
            or context.budget.max_tool_calls != 0
        ):
            raise ValueError("Runtime 输入身份、Schema 或权限不匹配")
        if context.budget.max_tokens is None or context.budget.timeout_seconds is None:
            raise ValueError("Runtime 需要显式预算")
        from openjiuwen.core.foundation.llm.schema.config import (
            ModelClientConfig,
            ModelRequestConfig,
        )
        from openjiuwen.core.single_agent.agents.react_agent import ReActAgentConfig

        schemas = {
            RoleType.PLANNER: (ANALYSIS_SCHEMA, PlanningAnalysis),
            RoleType.EXECUTOR: (PLAN_SCHEMA, ProjectPlan),
            RoleType.VERIFIER: (REVIEW_SCHEMA, PlanningReview),
            RoleType.CRITIC: (REVIEW_SCHEMA, PlanningReview),
        }
        schema_ref, schema = schemas[state.config.role]
        endpoint = state.endpoint
        timeout = min(
            endpoint.timeout_seconds,
            context.budget.timeout_seconds,
            state.config.runtime_config.timeout_seconds or endpoint.timeout_seconds,
        )
        output_cap = min(endpoint.max_output_tokens, context.budget.max_tokens)
        client = ModelClientConfig(
            client_provider="OpenAI",
            api_base=str(endpoint.base_url),
            api_key=endpoint.api_key.get_secret_value(),
            timeout=timeout,
            max_retries=0,
            use_shared_llm_http_client=False,
        )
        request = ModelRequestConfig.model_validate(
            {
                "model": endpoint.model_name,
                "temperature": endpoint.temperature,
                "top_p": endpoint.top_p,
                "max_tokens": output_cap,
                "response_format": {"type": "json_object"},
                # DeepSeek V4 默认启用思考模式，短预算会被 reasoning tokens 耗尽，
                # 导致结构化正文为空。v0 需要低成本、确定性的 JSON 输出。
                "extra_body": {"thinking": {"type": "disabled"}},
            }
        )
        prompt = (
            load_prompt(state.config.prompt_ref)
            + "\n只返回一个 JSON 对象，不使用 Markdown。\n"
            + "输出 JSON Schema：\n"
            + json.dumps(schema.model_json_schema(), ensure_ascii=False)
        )
        state.agent.configure(
            ReActAgentConfig(
                model_name=endpoint.model_name,
                model_client_config=client,
                model_config_obj=request,
                # 给 ReAct 留出有限的内部推理/收尾空间；EvoTeam 仍禁止未授权
                # Tool，且 Runtime 句柄仍只允许一次 invoke，避免无界循环。
                max_iterations=MAX_REACT_ITERATIONS,
                prompt_template=[{"role": "system", "content": prompt}],
            )
        )
        state.invoked = True
        state.running = True
        try:
            async with asyncio.timeout(timeout):
                await state.agent.invoke(
                    {
                        "query": json.dumps(message.payload, ensure_ascii=False),
                        "conversation_id": agent.handle_id,
                    }
                )
        finally:
            state.running = False
        if len(state.responses) != 1:
            raise ValueError("SDK 未返回唯一模型响应；拒绝隐藏调用")
        response = state.responses[0]
        raw = response.content
        try:
            output = json.loads(raw)
            if not isinstance(output, dict):
                raise ValueError("输出不是对象")
            if response.tool_calls or response.finish_reason != "stop":
                raise ValueError("意外工具请求或输出未完整终结")
        except (ValueError, TypeError):
            # 返回给 Orchestrator 保存并按角色 Schema 拒绝，不重试、不修饰为成功产物。
            output = {
                "raw_response": raw,
                "finish_reason": response.finish_reason,
                "unexpected_tool_calls": bool(response.tool_calls),
            }
        usage = response.usage_metadata
        # SDK 将供应商缺失的单项字段填成 0；非空请求和回答不应被登记为零用量。
        if usage is not None and (usage.input_tokens <= 0 or usage.output_tokens <= 0):
            usage = None
        return AgentResult(
            instance_id=agent.handle_id,
            output_schema=schema_ref,
            output=output,
            input_tokens=usage.input_tokens if usage is not None else None,
            output_tokens=usage.output_tokens if usage is not None else None,
        )

    async def close(self, agent: RuntimeAgent) -> None:
        state = self._sessions.get(agent.handle_id)
        if state is None or state.handle != agent:
            raise ValueError("未知 Runtime 句柄")
        if state.running:
            raise ValueError("必须先终结 invoke 再释放 Agent")
        from openjiuwen.core.session.checkpointer.checkpointer import CheckpointerFactory

        # SDK clear_session 经全局 Runner 引入无关 team/evolving 可选依赖；
        # 当前句柄只有单 Agent checkpoint 与 context，直接释放这两个公开资源。
        await CheckpointerFactory.get_checkpointer().release(session_id=agent.handle_id)
        await state.agent.context_engine.clear_context(session_id=agent.handle_id)
        state.responses.clear()
        del self._sessions[agent.handle_id]
