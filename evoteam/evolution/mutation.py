"""受白名单和 Schema 限制的候选生成；不读取 Validation 标准答案。"""

from evoteam.domain.common import StrategyRef
from evoteam.domain.evolution import MutationProposal
from evoteam.domain.experience import AttributionReport
from evoteam.domain.strategy import Strategy
from evoteam.monitoring.policy import EvolutionPolicy


class CandidateGenerator:
    async def propose(
        self,
        current: Strategy,
        attribution: AttributionReport,
        policy: EvolutionPolicy,
    ) -> tuple[MutationProposal, ...]:
        """P3: 提出少量最小修改，只能引用已有 Role 和授权能力。"""
        raise NotImplementedError("P3: Mutation 提案尚未实现")

    def materialize(
        self,
        current: Strategy,
        proposal: MutationProposal,
        *,
        candidate_ref: StrategyRef,
    ) -> Strategy:
        """P3: 校验提案并产生 CANDIDATE；唯一版本号由持久化层分配。

        必须保留 Current，不使用原地修改或 parent.version + 1 生成冲突身份。
        """
        raise NotImplementedError("P3: Candidate 构建与静态检查尚未实现")
