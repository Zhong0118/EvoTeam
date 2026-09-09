"""首个可执行监控规则：同类错误跨 Run 重复；其余信号等待基线与归因证据。"""

from collections.abc import Sequence

from evoteam.domain.evolution import EvolutionTrigger, MonitorResult, TriggerType
from evoteam.domain.run import SealedRun
from evoteam.domain.strategy import Strategy, StrategyStatus
from evoteam.experience.evidence import evidence_id, failure_codes, validate_window
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.monitoring.state import MonitorState


class StrategyMonitor:
    def inspect(
        self, strategy: Strategy, runs: Sequence[SealedRun], policy: EvolutionPolicy
    ) -> MonitorResult:
        """无状态规则测试入口；实际观察用 observe 并持久化检查点。"""
        return self.observe(strategy, runs, policy, MonitorState())[0]

    def observe(
        self,
        strategy: Strategy,
        runs: Sequence[SealedRun],
        policy: EvolutionPolicy,
        state: MonitorState,
    ) -> tuple[MonitorResult, MonitorState]:
        validate_window(runs)
        if strategy.metadata.status not in {StrategyStatus.CURRENT, StrategyStatus.STABLE}:
            raise ValueError("仅监控当前服务策略")
        if len(runs) > policy.window_size or any(
            run.strategy != strategy.metadata.ref for run in runs
        ):
            raise ValueError("监控窗口与策略或 Policy 不符")
        if policy.enabled_triggers != (TriggerType.REPEATED_FAILURE,):
            raise NotImplementedError("漂移、成本和贡献监控需要已登记基线；当前仅重复失败规则可用")
        fingerprint = evidence_id("policy", policy.model_dump())
        if state.policy_fingerprint not in (None, fingerprint):
            raise ValueError("同一 Policy 版本不能修改参数")
        ids = tuple(run.run_id for run in runs)
        if ids == state.last_window_ids and state.last_result is not None:
            return state.last_result, state
        seen = tuple(dict.fromkeys((*state.seen_run_ids, *ids)))
        reason = "未达到重复失败阈值"
        trigger = None
        if len(runs) < policy.min_samples:
            reason = "样本不足"
        elif (
            state.last_trigger_sample_count is not None
            and len(seen) - state.last_trigger_sample_count < policy.cooldown_runs
        ):
            reason = "冷却期内，继续收集新 Run"
        else:
            counts = {
                code: tuple(run.run_id for run in runs if code in failure_codes(run))
                for code in {code for run in runs for code in failure_codes(run)}
            }
            for code in sorted(counts, key=lambda key: (-len(counts[key]), key)):
                evidence = counts[code]
                if len(evidence) >= policy.repeated_failure_threshold:
                    reason = f"{code} 在 {len(evidence)} 个 Run 中重复出现"
                    identity = [
                        strategy.metadata.ref.model_dump(),
                        policy.model_dump(),
                        runs[0].task_scope,
                        runs[0].evaluation.evaluator_ref.model_dump(),
                        code,
                        evidence,
                    ]
                    trigger = EvolutionTrigger(
                        trigger_id=evidence_id("trigger", identity),
                        strategy=strategy.metadata.ref,
                        policy_ref=policy.ref,
                        trigger_type=TriggerType.REPEATED_FAILURE,
                        task_scope=runs[0].task_scope,
                        evidence_run_ids=evidence,
                        reason=reason,
                    )
                    break
        result = MonitorResult(
            strategy=strategy.metadata.ref, sample_count=len(runs), reason=reason, trigger=trigger
        )
        next_state = MonitorState(
            revision=state.revision + 1,
            policy_fingerprint=fingerprint,
            seen_run_ids=seen,
            last_trigger_sample_count=len(seen) if trigger else state.last_trigger_sample_count,
            last_window_ids=ids,
            last_result=result,
        )
        return result, next_state
