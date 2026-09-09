"""Strategy 生命周期服务；状态修改必须与审计及当前指针一致落盘。"""

from evoteam.domain.common import StrategyRef
from evoteam.domain.evolution import EvolutionRecord, GateDecision, GateResult
from evoteam.domain.strategy import StrategyStatus
from evoteam.storage.protocol import StrategyStore


class StrategyLifecycle:
    def __init__(self, store: StrategyStore) -> None:
        self.store = store

    async def promote(
        self, candidate: StrategyRef, gate: GateResult, record: EvolutionRecord
    ) -> None:
        """检查 PASS 与父版本，原子切换服务指针并保留旧快照。"""
        if gate.decision != GateDecision.PASS or record.promoted != candidate:
            raise ValueError("只有 Gate PASS 且记录一致的 Candidate 可以晋级")
        current = await self.store.current(candidate.strategy_id)
        selected = await self.store.get(candidate)
        if selected.metadata.parent != current.metadata.ref:
            raise ValueError("Candidate 不是当前服务版本的直接子版本")
        if selected.metadata.status not in {StrategyStatus.CANDIDATE, StrategyStatus.VALIDATING}:
            raise ValueError("只有 Candidate/Validating 版本可以晋级")
        retired = current.model_copy(
            update={
                "metadata": current.metadata.model_copy(update={"status": StrategyStatus.RETIRED})
            }
        )
        promoted = selected.model_copy(
            update={
                "metadata": selected.metadata.model_copy(update={"status": StrategyStatus.CURRENT})
            }
        )
        await self.store.apply_lifecycle(
            expected_current=current.metadata.ref,
            updated_versions=(retired, promoted),
            serving=candidate,
            record=record,
        )

    async def reject(
        self, candidate: StrategyRef, gate: GateResult, record: EvolutionRecord
    ) -> None:
        """拒绝未上线候选，保留负面证据，Current 保持可用。"""
        if gate.decision == GateDecision.PASS or record.promoted is not None:
            raise ValueError("PASS Candidate 不能走 Reject")
        current = await self.store.current(candidate.strategy_id)
        selected = await self.store.get(candidate)
        if selected.metadata.parent != current.metadata.ref:
            raise ValueError("Candidate 不是当前服务版本的直接子版本")
        if selected.metadata.status not in {StrategyStatus.CANDIDATE, StrategyStatus.VALIDATING}:
            raise ValueError("只有 Candidate/Validating 版本可以拒绝")
        rejected = selected.model_copy(
            update={
                "metadata": selected.metadata.model_copy(update={"status": StrategyStatus.REJECTED})
            }
        )
        await self.store.apply_lifecycle(
            expected_current=current.metadata.ref,
            updated_versions=(rejected,),
            serving=current.metadata.ref,
            record=record,
        )

    async def finalize_candidates(
        self,
        candidates: tuple[StrategyRef, ...],
        gates: tuple[GateResult, ...],
        record: EvolutionRecord,
        *,
        selected: StrategyRef | None,
    ) -> None:
        """一次事务统一晋级一个候选并拒绝其余候选。"""
        if (
            not candidates
            or len(candidates) != len(gates)
            or len(set(candidates)) != len(candidates)
        ):
            raise ValueError("候选与 Gate 必须非空、一一对应且身份唯一")
        if selected is not None and selected not in candidates:
            raise ValueError("晋级目标不在候选集合")
        if record.candidates != candidates or record.gate_results != gates:
            raise ValueError("生命周期输入与 EvolutionRecord 不一致")
        if record.promoted != selected:
            raise ValueError("EvolutionRecord 的 promoted 与选择结果不一致")
        current = await self.store.current(candidates[0].strategy_id)
        updated = []
        for ref, gate in zip(candidates, gates, strict=True):
            candidate = await self.store.get(ref)
            if candidate.metadata.parent != current.metadata.ref:
                raise ValueError("所有 Candidate 必须来自同一 Current")
            if candidate.metadata.status not in {
                StrategyStatus.CANDIDATE,
                StrategyStatus.VALIDATING,
            }:
                raise ValueError("候选已终结，不能重复应用")
            if ref == selected:
                if gate.decision != GateDecision.PASS:
                    raise ValueError("只有 Gate PASS 的 Candidate 可以晋级")
                status = StrategyStatus.CURRENT
            else:
                status = StrategyStatus.REJECTED
            updated.append(
                candidate.model_copy(
                    update={"metadata": candidate.metadata.model_copy(update={"status": status})}
                )
            )
        if selected is not None:
            updated.insert(
                0,
                current.model_copy(
                    update={
                        "metadata": current.metadata.model_copy(
                            update={"status": StrategyStatus.RETIRED}
                        )
                    }
                ),
            )
        await self.store.apply_lifecycle(
            expected_current=current.metadata.ref,
            updated_versions=tuple(updated),
            serving=selected or current.metadata.ref,
            record=record,
        )

    async def transition(
        self, strategy: StrategyRef, target: StrategyStatus, record: EvolutionRecord
    ) -> None:
        """校验合法的 Stable/Reopen 状态转换，不提供任意状态赋值。"""
        current = await self.store.current(strategy.strategy_id)
        if current.metadata.ref != strategy:
            raise ValueError("只能转换当前服务版本")
        allowed = {
            (StrategyStatus.CURRENT, StrategyStatus.STABLE),
            (StrategyStatus.STABLE, StrategyStatus.CURRENT),
        }
        if (current.metadata.status, target) not in allowed:
            raise ValueError("非法 Stable/Reopen 状态转换")
        updated = current.model_copy(
            update={"metadata": current.metadata.model_copy(update={"status": target})}
        )
        await self.store.apply_lifecycle(
            expected_current=strategy,
            updated_versions=(updated,),
            serving=strategy,
            record=record,
        )

    async def rollback(
        self, failed: StrategyRef, restore: StrategyRef, record: EvolutionRecord
    ) -> None:
        """记录退化版本，恢复历史可用版本；区别于 Reject。"""
        current = await self.store.current(failed.strategy_id)
        previous = await self.store.get(restore)
        if current.metadata.ref != failed or restore.strategy_id != failed.strategy_id:
            raise ValueError("Rollback 身份与当前服务版本不匹配")
        if record.rollback_target != restore:
            raise ValueError("治理记录缺少一致的 rollback_target")
        if previous.metadata.status not in {StrategyStatus.RETIRED, StrategyStatus.ROLLED_BACK}:
            raise ValueError("只能恢复已退出服务的历史版本")
        rolled_back = current.model_copy(
            update={
                "metadata": current.metadata.model_copy(
                    update={"status": StrategyStatus.ROLLED_BACK}
                )
            }
        )
        restored = previous.model_copy(
            update={
                "metadata": previous.metadata.model_copy(update={"status": StrategyStatus.CURRENT})
            }
        )
        await self.store.apply_lifecycle(
            expected_current=failed,
            updated_versions=(rolled_back, restored),
            serving=restore,
            record=record,
        )
