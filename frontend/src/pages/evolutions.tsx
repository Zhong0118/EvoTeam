import { StrategyDiff } from "../components/evidence/strategy-diff";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowRight, ArrowLeft, RefreshCw, ShieldCheck } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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
  human,
  number,
} from "../components/evidence/common";
import { defaultStrategy, useEvidence } from "../data/client";
import {
  evolutionDetailSchema,
  evolutionSchema,
  pageSchema,
  type Validation,
} from "../data/schema";
const listSchema = pageSchema(evolutionSchema);
export function Evolutions() {
  const [params, setParams] = useSearchParams();
  const strategy = params.get("strategy_id") ?? defaultStrategy;
  const query = useEvidence(
    strategy
      ? `/evolutions?${new URLSearchParams({ strategy_id: strategy, limit: "20", ...(params.get("cursor") ? { cursor: params.get("cursor")! } : {}) })}`
      : null,
    listSchema,
  );
  return (
    <>
      <PageTitle
        title="演进证据"
        description="了解为何触发、改了哪里，以及候选为何晋级或被拒绝。"
        actions={
          <Button onClick={query.refresh} disabled={!strategy}>
            <RefreshCw size={15} />
            刷新记录
          </Button>
        }
      />
      <form
        className="filter-bar"
        onSubmit={(e) => {
          e.preventDefault();
          setParams({
            strategy_id: String(new FormData(e.currentTarget).get("strategy")),
          });
        }}
      >
        <label className="inline-field">
          策略 ID{" "}
          <input
            name="strategy"
            key={strategy}
            defaultValue={strategy}
            placeholder="输入已登记的策略 ID"
          />
        </label>
        <Button type="submit">查询</Button>
      </form>
      <QueryState {...query} retry={query.refresh} />
      {!strategy && <Empty title="请输入策略 ID" />}
      {query.value && (
        <>
          <div className="evolution-feed">
            {query.value.data.items.map((r) => (
              <article className="evolution-card" key={r.evolution_id}>
                <div className="evolution-icon">
                  <ShieldCheck size={21} />
                </div>
                <div className="evolution-body">
                  <div className="section-heading">
                    <CopyId id={r.evolution_id} />
                    <Badge value={r.gate_results.at(-1)?.decision}>
                      {r.gate_results.length ? undefined : "尚无 Gate 证据"}
                    </Badge>
                  </div>
                  <h2>
                    {human(r.trigger.trigger_type)} · Strategy v
                    {r.trigger.strategy.version}
                  </h2>
                  <p>{r.trigger.reason}</p>
                  <div className="candidate-line">
                    <Badge>Current v{r.trigger.strategy.version}</Badge>
                    <ArrowRight size={14} />
                    {r.candidates.length ? (
                      r.candidates.map((c) => (
                        <Badge key={c.version} value="candidate">
                          Candidate v{c.version}
                        </Badge>
                      ))
                    ) : (
                      <span className="muted">未生成候选</span>
                    )}
                  </div>
                  <div className="card-foot">
                    <span className="tiny">
                      {r.trigger.evidence_run_ids.length} 个支持 Run ·{" "}
                      {r.candidates.length} 个候选
                    </span>
                    <Link
                      className="view-link"
                      to={`/dashboard/evolutions/${encodeURIComponent(r.evolution_id)}`}
                    >
                      查看证据链 <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
          {!query.value.data.items.length && (
            <Empty title="当前策略尚无演进记录" />
          )}
          <div className="pagination">
            <Button
              disabled={!params.get("cursor")}
              onClick={() => {
                const p = new URLSearchParams(params);
                const trail = p.getAll("prev");
                const previous = trail.pop();
                p.delete("prev");
                trail.forEach((v) => p.append("prev", v));
                if (previous) p.set("cursor", previous);
                else p.delete("cursor");
                setParams(p);
              }}
            >
              上一页
            </Button>
            <Button
              disabled={!query.value.data.next_cursor}
              onClick={() =>
                (() => {
                  const p = new URLSearchParams(params);
                  p.set("strategy_id", strategy);
                  p.append("prev", params.get("cursor") || "");
                  p.set("cursor", query.value!.data.next_cursor!);
                  setParams(p);
                })()
              }
            >
              下一页
            </Button>
          </div>
          <SourceNote envelope={query.value} />
        </>
      )}
    </>
  );
}
export function ValidationPanel({ value: v }: { value: Validation }) {
  const data = [
    { name: "Current", tokens: v.current_metrics.tokens },
    { name: "Candidate", tokens: v.candidate_metrics.tokens },
  ];
  return (
    <div className="validation-block">
      <h3>{v.validation_id}</h3>
      <p className="tiny">
        来源 {v.plan.dataset_ref.id}@{v.plan.dataset_ref.version} ·{" "}
        {v.plan.repeats} 次重复 · 独立任务{" "}
        {v.current_summary?.independent_task_count ?? "未提供"}
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>指标</th>
              <th>Current</th>
              <th>Candidate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>成功数 / 总数</td>
              <td>
                {v.current_summary
                  ? `${v.current_summary.success_count} / ${v.current_summary.total_count}`
                  : "未提供"}
              </td>
              <td>
                {v.candidate_summary
                  ? `${v.candidate_summary.success_count} / ${v.candidate_summary.total_count}`
                  : "未提供"}
              </td>
            </tr>
            {(
              [
                "tokens",
                "latency_seconds",
                "agent_count",
                "retry_count",
              ] as const
            ).map((k) => (
              <tr key={k}>
                <td>
                  {
                    {
                      tokens: "Token",
                      latency_seconds: "延迟（秒）",
                      agent_count: "Agent 数",
                      retry_count: "Retry",
                    }[k]
                  }
                </td>
                <td>{number(v.current_metrics[k])}</td>
                <td>{number(v.candidate_metrics[k])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.every((d) => d.tokens !== null) && (
        <div
          className="metric-chart"
          aria-label="同一验证记录的 Token 对比，数值见上表"
        >
          <ResponsiveContainer width="100%" height={170}>
            <BarChart
              data={data}
              layout="vertical"
              margin={{ left: 15, right: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" />
              <YAxis type="category" dataKey="name" width={85} />
              <Tooltip />
              <Bar
                dataKey="tokens"
                name="Token"
                fill="#397c84"
                barSize={22}
                radius={[0, 4, 4, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <div className="notice">
        {v.limitations.map((s) => (
          <p key={s}>{s}</p>
        ))}
      </div>
      {v.pairs.length ? (
        <details>
          <summary>逐题配对（{v.pairs.length}）</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>任务</th>
                  <th>子类 / 重复</th>
                  <th>Current Run</th>
                  <th>Candidate Run</th>
                </tr>
              </thead>
              <tbody>
                {v.pairs.map((p) => (
                  <tr key={`${p.task_id}-${p.repeat_index}`}>
                    <td>{p.task_id}</td>
                    <td>
                      {p.subclass} / {p.repeat_index}
                    </td>
                    <td>
                      <Link to={`/dashboard/runs/${p.current_run_id}`}>
                        {p.current_run_id}
                      </Link>
                    </td>
                    <td>
                      <Link to={`/dashboard/runs/${p.candidate_run_id}`}>
                        {p.candidate_run_id}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : (
        <p className="muted">未提供逐题配对数据</p>
      )}
    </div>
  );
}
export function EvolutionDetail() {
  const { evolutionId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const stage = params.get("stage") || "trigger";
  const query = useEvidence(`/evolutions/${encodeURIComponent(evolutionId)}`,
    evolutionDetailSchema,
  );
  const d = query.value?.data;
  const r = d?.record;
  const parent = d?.strategies.find(
    (s) => s.metadata.ref.version === r?.trigger.strategy.version,
  );
  const comparison = d?.strategies.find(
    (s) =>
      s.metadata.ref.version ===
      Number(params.get("candidate") ?? r?.candidates[0]?.version),
  );
  const stages = [
    ["trigger", "触发信号"],
    ["attribution", "证据与归因"],
    ["candidate", "候选差异"],
    ["validation", "独立验证"],
    ["gate", "Gate 决定"],
  ];
  return (
    <>
      <Link className="back-link" to="/dashboard/evolutions">
        <ArrowLeft size={14} /> 演进记录
      </Link>
      <PageTitle title="演进证据链" description={evolutionId} />
      <QueryState {...query} retry={query.refresh} />
      {r && d && (
        <>
          <div className="stage-nav">
            {stages.map(([id, label], i) => (
              <button
                className={stage === id ? "selected" : ""}
                aria-pressed={stage === id}
                key={id}
                onClick={() => setParams({ stage: id })}
              >
                <span>{i + 1}</span>
                {label}
                {i < 4 && <ArrowRight size={14} />}
              </button>
            ))}
          </div>
          <div className="columns">
            <Panel
              title={stages.find((s) => s[0] === stage)?.[1] || "触发信号"}
            >
              {stage === "trigger" && (
                <>
                  <Badge>{human(r.trigger.trigger_type)}</Badge>
                  <h3 className="task-heading">{r.trigger.reason}</h3>
                  <p>
                    规则 {r.trigger.policy_ref.id}@
                    {r.trigger.policy_ref.version}
                  </p>
                  <h3>支持样本</h3>
                  {r.trigger.evidence_run_ids.length ? (
                    r.trigger.evidence_run_ids.map((id) => (
                      <p key={id}>
                        <Link to={`/dashboard/runs/${encodeURIComponent(id)}`}>
                          {id} →
                        </Link>
                      </p>
                    ))
                  ) : (
                    <Empty title="未提供支持 Run" />
                  )}
                </>
              )}
              {stage === "attribution" && (
                <>
                  {d.attributions.length ? (
                    d.attributions.map((a, i) => (
                      <div key={i}>
                        <h3>{a.report_id}</h3>
                        <Badge>
                          {a.needs_more_evidence
                            ? "需要更多证据"
                            : "已有归因记录"}
                        </Badge>
                        {a.claims.map((claim, j) => (
                          <div className="issue" key={j}>
                            <strong>
                              {claim.kind} · {claim.target}
                            </strong>
                            <p>{claim.explanation}</p>
                            <p className="tiny">
                              报告置信度 {claim.confidence} · 这是归因陈述
                            </p>
                            <p className="tiny">
                              证据：{claim.evidence_refs.join("、") || "未提供"}
                            </p>
                          </div>
                        ))}
                        <Raw value={a} />
                      </div>
                    ))
                  ) : (
                    <Empty title="尚无归因证据">
                      不能仅凭 Trigger 推定错误起点或因果关系。
                    </Empty>
                  )}
                </>
              )}
              {stage === "candidate" && (
                <>
                  {!d.proposals.length && <Empty title="未提供候选提案" />}
                  {d.proposals.map((p) => (
                    <div key={p.proposal_id}>
                      <Badge value="candidate">{human(p.operation)}</Badge>
                      <h3>{p.target}</h3>
                      <p>{p.rationale}</p>
                      <p className="tiny">归因引用：{p.attribution_ref}</p>
                    </div>
                  ))}
                  {r.candidates.length > 0 && (
                    <label className="field-label">
                      比较候选
                      <select
                        value={comparison?.metadata.ref.version ?? ""}
                        onChange={(e) =>
                          setParams({
                            stage: "candidate",
                            candidate: e.target.value,
                          })
                        }
                      >
                        {r.candidates.map((c) => (
                          <option key={c.version} value={c.version}>
                            Candidate v{c.version}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  {parent && comparison ? (
                    <StrategyDiff left={parent} right={comparison} />
                  ) : (
                    <p className="muted">
                      未提供完整的 Current / Candidate 配置。
                    </p>
                  )}
                  <Raw value={d.strategies} title="查看完整配置与连边差异" />
                </>
              )}
              {stage === "validation" && (
                <>
                  {d.validations.length ? (
                    d.validations.map((v) => (
                      <ValidationPanel key={v.validation_id} value={v} />
                    ))
                  ) : (
                    <Empty title="尚无独立验证证据" />
                  )}
                </>
              )}
              {stage === "gate" && (
                <>
                  {r.gate_results.length ? (
                    r.gate_results.map((g) => (
                      <div key={g.validation_id}>
                        <Badge value={g.decision} />
                        <h3>
                          规则 {g.policy_ref.id}@{g.policy_ref.version}
                        </h3>
                        {g.reasons.map((s) => (
                          <p className="notice" key={s}>
                            {s}
                          </p>
                        ))}
                        <p className="tiny">验证引用：{g.validation_id}</p>
                      </div>
                    ))
                  ) : (
                    <Empty title="尚无 Gate 证据" />
                  )}
                </>
              )}
            </Panel>
            <div className="stack">
              <Panel title="决定与依据" aside={<ShieldCheck size={18} />}>
                <div className="decision-label">
                  {r.promoted
                    ? "已记录晋级"
                    : r.gate_results.length
                      ? "候选尚未晋级"
                      : "尚无决定"}
                </div>
                <p className="muted">
                  {r.termination_reason || "仅展示已经保存的治理记录。"}
                </p>
                {r.gate_results.map((g) => (
                  <div key={g.validation_id} className="issue">
                    <Badge value={g.decision} />
                    {g.reasons.map((s) => (
                      <p key={s}>{s}</p>
                    ))}
                  </div>
                ))}
                <Link
                  className="view-link"
                  to={`/dashboard/strategies/${r.trigger.strategy.strategy_id}`}
                >
                  查看策略版本 <ArrowRight size={14} />
                </Link>
              </Panel>
              <div className="notice">
                Gate 的决定与服务版本切换分别记录。证据不足时不能推定晋级。
              </div>
            </div>
          </div>
          <SourceNote envelope={query.value!} />
        </>
      )}
    </>
  );
}
