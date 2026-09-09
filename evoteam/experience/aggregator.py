"""归纳重复错误和成功反例；不把观察相关性当作因果归因。"""

from collections.abc import Sequence

from evoteam.domain.experience import FailureExperience, OutcomePattern
from evoteam.domain.run import SealedRun
from evoteam.experience.evidence import evidence_id, failure_codes, validate_window


class ExperienceAggregator:
    def aggregate(self, runs: Sequence[SealedRun]) -> tuple[OutcomePattern, ...]:
        validate_window(runs)
        if not runs:
            return ()
        first = runs[0]
        codes = sorted({code for run in runs for code in failure_codes(run)})
        patterns = []
        for code in codes:
            support = tuple(run.run_id for run in runs if code in failure_codes(run))
            if len(support) < 2:
                continue
            counterexamples = tuple(
                run.run_id
                for run in runs
                if run.evaluation.metrics.success is True and code not in failure_codes(run)
            )
            identity = [
                first.strategy.model_dump(),
                first.task_scope,
                first.evaluation.evaluator_ref.model_dump(),
                code,
                support,
                counterexamples,
            ]
            experience = FailureExperience(
                experience_id=evidence_id("failure", identity),
                strategy=first.strategy,
                task_scope=first.task_scope,
                failure_pattern=code,
                supporting_runs=support,
                counterexample_runs=counterexamples,
            )
            patterns.append(
                OutcomePattern(
                    pattern_id=evidence_id(
                        "pattern", [identity, tuple(run.run_id for run in runs)]
                    ),
                    strategy=first.strategy,
                    task_scope=first.task_scope,
                    supporting_runs=tuple(run.run_id for run in runs),
                    failures=(experience,),
                )
            )
        return tuple(patterns)
