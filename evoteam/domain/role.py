from enum import StrEnum
from types import MappingProxyType

from evoteam.domain.common import FrozenModel


class RoleType(StrEnum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    VERIFIER = "verifier"
    CRITIC = "critic"


class RoleDefinition(FrozenModel):
    role: RoleType
    responsibility: str


ROLE_POOL = MappingProxyType(
    {
        RoleType.PLANNER: RoleDefinition(
            role=RoleType.PLANNER, responsibility="理解任务目标与约束，拆解工作并制定执行计划"
        ),
        RoleType.EXECUTOR: RoleDefinition(
            role=RoleType.EXECUTOR, responsibility="根据计划使用已授权能力，形成任务产物与执行证据"
        ),
        RoleType.RESEARCHER: RoleDefinition(
            role=RoleType.RESEARCHER, responsibility="整理资料、核对来源并收集可追溯证据"
        ),
        RoleType.ANALYST: RoleDefinition(
            role=RoleType.ANALYST, responsibility="分析数据、计算指标并解释结果与口径"
        ),
        RoleType.WRITER: RoleDefinition(
            role=RoleType.WRITER, responsibility="组织材料，生成结构清晰且有依据的最终表达"
        ),
        RoleType.VERIFIER: RoleDefinition(
            role=RoleType.VERIFIER, responsibility="独立校验事实、数值与不可违反的硬约束"
        ),
        RoleType.CRITIC: RoleDefinition(
            role=RoleType.CRITIC, responsibility="审查当前产物的完整性与问题，给出通过或返工意见"
        ),
    }
)
