"""只有 Trigger 后启动的离线总控；不亲自打分或决定 Gate。"""

from collections.abc import Sequence

from evoteam.domain.common import StrategyRef
from evoteam.domain.evolution import (
    EvolutionRecord,
    EvolutionTrigger,
    GateDecision,
    GateResult,
    ValidationPlan,
    ValidationResult,
)
from evoteam.domain.run import SealedRun
from evoteam.domain.strategy import Strategy
from evoteam.evolution.attribution import OutcomeAttributor
from evoteam.evolution.gate import GatePolicy, ValidationGate
from evoteam.evolution.lifecycle import StrategyLifecycle
from evoteam.evolution.mutation import CandidateGenerator
from evoteam.evolution.validator import ValidationRunner
from evoteam.experience.evidence import evidence_id
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.storage.protocol import EvolutionStore, StrategyStore


class EvolutionManager:
    def __init__(
        self,
        attributor: OutcomeAttributor,
        generator: CandidateGenerator,
        validator: ValidationRunner,
        gate: ValidationGate,
        lifecycle: StrategyLifecycle,
        strategies: StrategyStore,
        records: EvolutionStore,
    ) -> None:
        self.attributor = attributor
        self.generator = generator
        self.validator = validator
        self.gate = gate
        self.lifecycle = lifecycle
        self.strategies = strategies
        self.records = records

    async def evolve(
        self,
        trigger: EvolutionTrigger,
        current: Strategy,
        evidence: Sequence[SealedRun],
        policy: EvolutionPolicy,
        validation_plan: ValidationPlan,
        gate_policy: GatePolicy,
    ) -> EvolutionRecord:
        """校验 Trigger → 归因 → 候选 → 实验 → 改进归因 → Gate → 生命周期。

        一个调用可比较多个单因素候选；异常验证会拒绝对应候选并留下治理记录。
        CandidateGenerator 不接收 validation_plan 或验证答案。
        """
        if trigger.strategy != current.metadata.ref or trigger.policy_ref != policy.ref:
            raise ValueError("Trigger 与 Current 或 EvolutionPolicy 不匹配")
        evidence_by_id = {run.run_id: run for run in evidence}
        if set(trigger.evidence_run_ids) - set(evidence_by_id):
            raise ValueError("演进证据缺少 Trigger 引用的 Run")
        if any(
            run.strategy != current.metadata.ref or run.task_scope != trigger.task_scope
            for run in evidence
        ):
            raise ValueError("演进证据与 Trigger 范围不匹配")
        evolution_id = evidence_id(
            "evolution", [trigger.trigger_id, current.metadata.ref.model_dump()]
        )
        attribution = await self.attributor.analyze_failure(evidence)
        await self.records.save_attribution(attribution)
        proposals = await self.generator.propose(current, attribution, policy)
        for proposal in proposals:
            await self.records.save_proposal(proposal)
        if not proposals:
            record = EvolutionRecord(
                evolution_id=evolution_id,
                trigger=trigger,
                attribution_refs=(attribution.report_id,),
            )
            await self.records.save_record(record)
            return record

        candidate_refs = []
        validations: dict[StrategyRef, ValidationResult] = {}
        validation_refs = []
        attribution_refs = [attribution.report_id]
        gates = []
        for proposal in proposals:
            candidate_ref = await self.strategies.allocate_version(current.metadata.ref.strategy_id)
            candidate = self.generator.materialize(current, proposal, candidate_ref=candidate_ref)
            await self.strategies.save(candidate)
            candidate_refs.append(candidate_ref)
            try:
                validation = await self.validator.validate(current, candidate, validation_plan)
                await self.records.save_validation(validation)
                improvement = await self.attributor.analyze_improvement(validation)
                await self.records.save_attribution(improvement)
                gate = self.gate.decide(validation, improvement, gate_policy)
                validations[candidate_ref] = validation
                validation_refs.append(validation.validation_id)
                attribution_refs.append(improvement.report_id)
            except Exception as exc:
                gate = GateResult(
                    validation_id=f"failed:{candidate_ref.version}",
                    decision=GateDecision.FAIL,
                    policy_ref=gate_policy.ref,
                    reasons=(f"验证流程异常：{type(exc).__name__}",),
                    improvement_attribution_ref=attribution.report_id,
                )
            gates.append(gate)

        passing = [
            ref
            for ref, gate in zip(candidate_refs, gates, strict=True)
            if gate.decision == GateDecision.PASS and ref in validations
        ]
        promoted = (
            max(passing, key=lambda ref: self._selection_key(validations[ref], ref.version))
            if passing
            else None
        )
        record = EvolutionRecord(
            evolution_id=evolution_id,
            trigger=trigger,
            attribution_refs=tuple(attribution_refs),
            proposal_refs=tuple(proposal.proposal_id for proposal in proposals),
            candidates=tuple(candidate_refs),
            validation_refs=tuple(validation_refs),
            gate_results=tuple(gates),
            promoted=promoted,
        )
        await self.lifecycle.finalize_candidates(
            tuple(candidate_refs), tuple(gates), record, selected=promoted
        )
        return record

    @staticmethod
    def _selection_key(result: ValidationResult, version: int) -> tuple[float, ...]:
        """质量优先，其次错误减少，再比较 Token/延迟；低版本作为稳定平局规则。"""
        current = result.current_metrics
        candidate = result.candidate_metrics
        success_gain = float(candidate.success is True) - float(current.success is True)
        error_gain = (
            float(current.hard_constraint_errors - candidate.hard_constraint_errors)
            if current.hard_constraint_errors is not None
            and candidate.hard_constraint_errors is not None
            else 0.0
        )
        quality_gain = (
            candidate.quality - current.quality
            if current.quality is not None and candidate.quality is not None
            else 0.0
        )
        token_gain = (
            float(current.tokens - candidate.tokens)
            if current.tokens is not None and candidate.tokens is not None
            else 0.0
        )
        latency_gain = (
            current.latency_seconds - candidate.latency_seconds
            if current.latency_seconds is not None and candidate.latency_seconds is not None
            else 0.0
        )
        return success_gain, error_gain, quality_gain, token_gain, latency_gain, -float(version)
