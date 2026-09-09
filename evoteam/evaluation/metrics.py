"""从唯一 AgentResult 统计用量；不重复累计转发消息，不推测供应商费用。"""

from collections.abc import Sequence

from evoteam.domain.evaluation import RunMetrics
from evoteam.domain.events import TraceEvent
from evoteam.domain.run import RunResult, RunStatus


class MetricsCollector:
    def collect(self, run: RunResult, events: Sequence[TraceEvent] = ()) -> RunMetrics:
        tokens = None
        if (
            run.status == RunStatus.COMPLETED
            and run.results
            and all(
                result.input_tokens is not None and result.output_tokens is not None
                for result in run.results
            )
        ):
            tokens = sum((r.input_tokens or 0) + (r.output_tokens or 0) for r in run.results)
        # events 供后续工具/返工实现解析；当前固定 v0 的执行计数由控制器提供。
        return RunMetrics(
            tokens=tokens,
            agent_count=len(run.team.instances) if run.team else None,
            latency_seconds=run.latency_seconds,
            tool_calls=run.tool_calls,
            retry_count=run.retry_count,
        )
