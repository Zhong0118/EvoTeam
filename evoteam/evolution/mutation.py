"""受白名单和 Schema 限制的候选生成；不读取 Validation 标准答案。"""

from evoteam.capabilities.prompts import load_prompt
from evoteam.domain.agent import AgentConfig
from evoteam.domain.common import AssetRef, StrategyRef
from evoteam.domain.evolution import MutationProposal, MutationType
from evoteam.domain.experience import AttributionKind, AttributionReport
from evoteam.domain.role import RoleType
from evoteam.domain.run import RunPurpose
from evoteam.domain.strategy import Edge, Strategy, StrategyStatus
from evoteam.experience.evidence import evidence_id
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.orchestration.orchestrator import validate_strategy


class CandidateGenerator:
    """确定性生成器：只引用登记 Prompt/Role，不生成自由代码或权限。"""

    def __init__(self, replacements: dict[str, AssetRef] | None = None) -> None:
        self.replacements = dict(
            replacements or {"executor": AssetRef(id="executor", version="v1-resource-check")}
        )

    async def propose(
        self,
        current: Strategy,
        attribution: AttributionReport,
        policy: EvolutionPolicy,
    ) -> tuple[MutationProposal, ...]:
        """按 Origin/Control 归因提出 Prompt 替换和可选 Verifier。"""
        if attribution.strategy != current.metadata.ref:
            raise ValueError("归因报告与 Current 不匹配")
        by_node = {agent.node_id: agent for agent in current.definition.agents}
        proposals: list[MutationProposal] = []
        for claim in attribution.claims:
            if claim.kind != AttributionKind.ORIGIN or claim.confidence < 0.5:
                continue
            replacement = self.replacements.get(claim.target)
            agent = by_node.get(claim.target)
            if replacement is None or agent is None or replacement == agent.prompt_ref:
                continue
            load_prompt(replacement)
            proposal_id = evidence_id(
                "mutation",
                [
                    current.metadata.ref.model_dump(),
                    claim.target,
                    replacement.model_dump(),
                    claim.evidence_refs,
                ],
            )
            proposals.append(
                MutationProposal(
                    proposal_id=proposal_id,
                    parent=current.metadata.ref,
                    operation=MutationType.UPDATE_PROMPT,
                    target=claim.target,
                    rationale=claim.explanation,
                    attribution_ref=attribution.report_id,
                    replacement_ref=replacement,
                )
            )
            if len(proposals) >= policy.max_candidates:
                break
        if len(proposals) < policy.max_candidates and any(
            claim.kind == AttributionKind.CONTROL and claim.target == "critic"
            for claim in attribution.claims
        ):
            replacement = AssetRef(id="verifier", version="v0")
            load_prompt(replacement)
            proposals.append(
                MutationProposal(
                    proposal_id=evidence_id(
                        "mutation",
                        [
                            current.metadata.ref.model_dump(),
                            "add-verifier",
                            replacement.model_dump(),
                        ],
                    ),
                    parent=current.metadata.ref,
                    operation=MutationType.ADD_AGENT_CONFIG,
                    target="verifier",
                    rationale="增加独立 Verifier，在 Critic 前提供硬约束复核意见。",
                    attribution_ref=attribution.report_id,
                    replacement_ref=replacement,
                )
            )
        return tuple(proposals)

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
        if proposal.parent != current.metadata.ref:
            raise ValueError("Mutation 的父版本与 Current 不匹配")
        if proposal.operation not in {MutationType.UPDATE_PROMPT, MutationType.ADD_AGENT_CONFIG}:
            raise ValueError("当前只允许 UPDATE_PROMPT 或 ADD_AGENT_CONFIG")
        if proposal.replacement_ref is None:
            raise ValueError("Mutation 必须引用已登记的版本化资产")
        if candidate_ref.strategy_id != current.metadata.ref.strategy_id:
            raise ValueError("Candidate 不能改变 strategy_id")
        if candidate_ref == current.metadata.ref:
            raise ValueError("Candidate 必须使用独立版本")
        load_prompt(proposal.replacement_ref)
        edges = current.definition.edges
        if proposal.operation == MutationType.UPDATE_PROMPT:
            matches = [
                agent for agent in current.definition.agents if agent.node_id == proposal.target
            ]
            if len(matches) != 1:
                raise ValueError("Mutation target 必须唯一命中一个 AgentConfig")
            agents = tuple(
                agent.model_copy(
                    update={
                        "prompt_ref": proposal.replacement_ref,
                        "config_version": agent.config_version + 1,
                    }
                )
                if agent.node_id == proposal.target
                else agent
                for agent in current.definition.agents
            )
        else:
            if proposal.target != "verifier" or any(
                agent.role == RoleType.VERIFIER for agent in current.definition.agents
            ):
                raise ValueError("当前 ADD_AGENT_CONFIG 只允许新增唯一 Verifier")
            executor = next(
                agent for agent in current.definition.agents if agent.role == RoleType.EXECUTOR
            )
            critic = next(
                agent for agent in current.definition.agents if agent.role == RoleType.CRITIC
            )
            verifier = AgentConfig(
                node_id="verifier",
                config_id="planning-verifier",
                config_version=0,
                role=RoleType.VERIFIER,
                prompt_ref=proposal.replacement_ref,
                model_ref=executor.model_ref,
                runtime_config=critic.runtime_config,
            )
            agents = tuple(
                verifier if agent.role == RoleType.CRITIC else agent
                for agent in current.definition.agents
            ) + (critic,)
            edges = current.definition.edges + (
                Edge(source=executor.node_id, target=verifier.node_id),
                Edge(source=verifier.node_id, target=critic.node_id),
            )
        candidate = current.model_copy(
            update={
                "definition": current.definition.model_copy(
                    update={"agents": agents, "edges": edges}
                ),
                "metadata": current.metadata.model_copy(
                    update={
                        "ref": candidate_ref,
                        "parent": current.metadata.ref,
                        "generation": current.metadata.generation + 1,
                        "status": StrategyStatus.CANDIDATE,
                    }
                ),
            }
        )
        validate_strategy(candidate, RunPurpose.VALIDATION)
        return candidate
