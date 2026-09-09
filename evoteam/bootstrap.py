"""组装固定项目规划 v0；只构建配置，不创建 Agent 或启用服务。"""

from evoteam.domain.agent import AgentConfig
from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.role import RoleType
from evoteam.domain.strategy import Edge, Strategy, StrategyDefinition, StrategyVersionMetadata


def build_v0_strategy(*, model_ref: AssetRef) -> Strategy:
    """模型由调用者传入；生成 DRAFT，预算/授权/注册检查通过后才可启用。"""
    agents = tuple(
        AgentConfig(
            node_id=role.value,
            config_id=f"planning-{role.value}",
            config_version=0,
            role=role,
            prompt_ref=AssetRef(id=role.value, version="v0"),
            model_ref=model_ref,
        )
        for role in (RoleType.PLANNER, RoleType.EXECUTOR, RoleType.CRITIC)
    )
    return Strategy(
        definition=StrategyDefinition(
            agents=agents,
            edges=(
                Edge(source="planner", target="executor"),
                Edge(source="executor", target="critic"),
            ),
        ),
        metadata=StrategyVersionMetadata(
            ref=StrategyRef(strategy_id="project-planning", version=0)
        ),
    )
