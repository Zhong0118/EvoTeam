import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Network,
  Download,
  Clock3,
  CircleCheck,
} from "lucide-react";
import { Button } from "../components/ui/button";
import {
  Badge,
  CopyId,
  Empty,
  PageTitle,
  Panel,
  QueryState,
  Raw,
  SourceNote,
  number,
} from "../components/evidence/common";
import { source, useEvidence } from "../data/client";
import { runSchema } from "../data/schema";
export function RunDetail() {
  const { runId = "" } = useParams();
  const query = useEvidence(`/runs/${encodeURIComponent(runId)}`, runSchema);
  const [downloadError, setDownloadError] = useState("");
  const r = query.value?.data;
  async function download() {
    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE || ""}/v1/runs/${encodeURIComponent(runId)}/export`,
        { method: "GET" },
      );
      if (!res.ok) throw Error("证据导出失败，请重试");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "evoteam-run-evidence.json";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : "导出失败");
    }
  }
  return (
    <>
      <Link className="back-link" to="/runs">
        <ArrowLeft size={14} /> 运行记录
      </Link>
      <PageTitle
        title="任务详情"
        description="查看封存产物、硬约束校验与执行用量。"
        actions={
          <>
            <Button asChild variant="default">
              <Link to={`/runs/${encodeURIComponent(runId)}/trace`}>
                <Network size={16} />
                查看 Trace
              </Link>
            </Button>
            {source === "api" && r && (
              <Button onClick={download}>
                <Download size={15} />
                下载证据
              </Button>
            )}
          </>
        }
      />
      <QueryState {...query} retry={query.refresh} />
      {downloadError && <p role="alert">{downloadError}</p>}
      {r && (
        <>
          <div className="record-strip">
            <CopyId id={r.run_id} />
            <Badge value={r.status} />
            <Badge value={r.purpose} />
            <Link
              className="version-link"
              to={`/strategies/${r.strategy.strategy_id}`}
            >
              Strategy v{r.strategy.version}
            </Link>
          </div>
          <div className="columns">
            <div className="stack">
              <Panel title="任务与计划" aside={<Badge>封存快照</Badge>}>
                {r.task ? (
                  <>
                    <h3 className="task-heading">
                      {r.task.inputs?.goal || r.task.instruction}
                    </h3>
                    <p className="muted">{r.task.instruction}</p>
                    {r.task.inputs && (
                      <div className="constraint-strip">
                        <span>
                          <Clock3 size={15} /> 截止{" "}
                          {r.task.inputs.deadline_hour} 小时
                        </span>
                        <span>{r.task.inputs.people.length} 位人员</span>
                        <span>
                          预算 {number(r.task.inputs.budget_minor)} 最小货币单位
                          · {r.task.inputs.currency}
                        </span>
                      </div>
                    )}
                    {r.plan ? (
                      <>
                        <div className="table-scroll">
                          <table>
                            <thead>
                              <tr>
                                <th>工作项 / 依赖</th>
                                <th>人员</th>
                                <th>开始</th>
                                <th>结束</th>
                              </tr>
                            </thead>
                            <tbody>
                              {r.plan.schedule.map((w) => (
                                <tr key={w.work_id} id={`work-${w.work_id}`}>
                                  <td>
                                    <strong>
                                      {r.task?.inputs?.work_items.find(
                                        (x) => x.work_id === w.work_id,
                                      )?.description || w.work_id}
                                    </strong>
                                    <div className="tiny">
                                      {w.work_id} · 依赖{" "}
                                      {r.task?.inputs?.work_items
                                        .find((x) => x.work_id === w.work_id)
                                        ?.dependencies.join("、") || "无"}
                                    </div>
                                  </td>
                                  <td>{w.person_id}</td>
                                  <td className="mono">{w.start_hour} h</td>
                                  <td className="mono">{w.end_hour} h</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        <p className="tiny">
                          h
                          为从项目开始计算的整数小时，结束点不包含在占用区间内。
                        </p>
                      </>
                    ) : (
                      <Empty title="未提供结构化计划" />
                    )}
                  </>
                ) : (
                  <Empty title="该记录未提供完整任务快照">
                    保留已封存的状态和指标；无法重建排期。
                  </Empty>
                )}
              </Panel>
              {r.plan && (
                <Panel title="风险与校验依据">
                  <h3>风险</h3>
                  {r.plan.risks.length ? (
                    r.plan.risks.map((s, i) => (
                      <p key={i} className="notice">
                        {s}
                      </p>
                    ))
                  ) : (
                    <p className="muted">没有记录风险条目</p>
                  )}
                  <h3>校验说明</h3>
                  {r.plan.validation_notes.map((s, i) => (
                    <p key={i} className="muted">
                      {s}
                    </p>
                  ))}
                  <Raw value={r.plan} />
                </Panel>
              )}
            </div>
            <div className="stack">
              <Panel title="独立评价" aside={<CircleCheck size={18} />}>
                <div
                  className={`verdict ${r.evaluation.metrics.success === false ? "error-text" : ""}`}
                >
                  {r.evaluation.metrics.success == null
                    ? "尚无结论"
                    : r.evaluation.metrics.success
                      ? "校验通过"
                      : "校验未通过"}
                </div>
                <p className="muted">
                  {r.evaluation.evaluator_ref.id}@
                  {r.evaluation.evaluator_ref.version}
                </p>
                {r.evaluation.issues.map((issue, i) => (
                  <div className="issue" key={i}>
                    <strong>{issue.code}</strong>
                    <p>{issue.message}</p>
                    {issue.evidence_refs.map((ref) => {
                      const id = ref.startsWith("work:") ? ref.slice(5) : null;
                      return id &&
                        r.plan?.schedule.some((w) => w.work_id === id) ? (
                        <a href={`#work-${id}`} key={ref}>
                          {ref} →
                        </a>
                      ) : (
                        <div key={ref} className="tiny">
                          {ref} · 无法定位
                        </div>
                      );
                    })}
                  </div>
                ))}
                <p className="tiny">运行完成与评价通过分别记录。</p>
              </Panel>
              <Panel title="执行用量">
                <dl className="metrics-list">
                  {[
                    ["Token", number(r.evaluation.metrics.tokens)],
                    [
                      "耗时",
                      number(r.evaluation.metrics.latency_seconds, " s"),
                    ],
                    ["Agent 数", number(r.evaluation.metrics.agent_count)],
                    ["Retry", number(r.evaluation.metrics.retry_count)],
                    ["工具调用", number(r.evaluation.metrics.tool_calls)],
                    ["金额", "未提供币种与来源"],
                    ["终止原因", r.termination_reason || "未提供"],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>{v}</dd>
                    </div>
                  ))}
                </dl>
              </Panel>
              <div className="notice">
                <p>
                  关联演进需由实际引用确认。此接口未提供反向关联索引，可从演进记录的证据入口追溯
                  Run。
                </p>
              </div>
            </div>
          </div>
          <SourceNote envelope={query.value!} />
        </>
      )}
    </>
  );
}
