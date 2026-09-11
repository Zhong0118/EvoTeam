import { useMemo, useState } from "react";
import { useEvidence } from "../../data/client";
import { evolutionDetailSchema, type Evolution } from "../../data/schema";
import { human } from "../../components/evidence/common";

function MiniStrategy({
  title,
  agents,
  edges,
  changed,
}: {
  title: string;
  agents: { node_id: string; role: string }[];
  edges: { source: string; target: string }[];
  changed: Set<string>;
}) {
  const depth = new Map<string, number>();
  const depthOf = (id: string, seen = new Set<string>()): number => {
    if (depth.has(id)) return depth.get(id)!;
    if (seen.has(id)) return 0;
    seen.add(id);
    const parents = edges.filter((e) => e.target === id).map((e) => e.source);
    const d =
      parents.length === 0 ? 0 : Math.max(...parents.map((p) => depthOf(p, seen))) + 1;
    depth.set(id, d);
    return d;
  };
  const layers = new Map<number, string[]>();
  for (const a of agents) {
    const d = depthOf(a.node_id);
    layers.set(d, [...(layers.get(d) ?? []), a.node_id]);
  }
  return (
    <div className="ws-evo-graph">
      <div className="ws-evo-graph-title">{title}</div>
      {edges.map((e, i) => {
        const from = depthOf(e.source);
        const to = depthOf(e.target);
        return (
          <span
            key={i}
            className="ws-mini-edge"
            style={{
              left: "50%",
              top: `${14 + from * 30 + 7}%`,
              height: `${(to - from) * 30 - 12}%`,
            }}
          />
        );
      })}
      {agents.map((a) => (
        <button
          key={a.node_id}
          type="button"
          className={`ws-mini-node ${changed.has(a.node_id) ? "changed" : ""}`}
          style={{
            left: "50%",
            top: `${14 + depthOf(a.node_id) * 30}%`,
          }}
        >
          {a.role}
          {changed.has(a.node_id) && <span className="ws-new-tag">CHANGED</span>}
        </button>
      ))}
    </div>
  );
}

const configFingerprint = (agent: {
  prompt_ref?: { id: string; version: string };
  model_ref?: { id: string; version: string };
  tool_policy?: unknown;
}): string =>
  JSON.stringify([agent.prompt_ref, agent.model_ref, agent.tool_policy]);

function delta(current: number | null, candidate: number | null) {
  if (current === null || candidate === null || current === 0) return null;
  return ((candidate - current) / current) * 100;
}

export function EvolutionView({
  strategyId,
  records,
  onOpenDiff,
}: {
  strategyId: string;
  records: Evolution[];
  onOpenDiff: (payload: {
    evolutionId: string;
    target: string;
    changedFields: { minus: string[]; plus: string[] };
    metrics: { label: string; current: number | null; candidate: number | null; goodWhenDown: boolean }[];
    gate: { decision: string; reasons: string[] } | null;
  }) => void;
}) {
  const [selected, setSelected] = useState(0);
  const record = records[selected];
  const detail = useEvidence(
    record ? `/evolutions/${encodeURIComponent(record.evolution_id)}` : null,
    evolutionDetailSchema,
  );
  const d = detail.value?.data;
  const currentStrategy = d?.strategies[0];
  const candidateStrategy = d?.strategies.find(
    (s) =>
      s.metadata.ref.version !== currentStrategy?.metadata.ref.version &&
      s.metadata.status !== "current",
  );
  const changed = useMemo(() => {
    const changedSet = new Set<string>();
    if (!currentStrategy || !candidateStrategy) return changedSet;
    const currentFp = new Map(
      currentStrategy.definition.agents.map((a) => [a.node_id, configFingerprint(a)]),
    );
    for (const agent of candidateStrategy.definition.agents) {
      if (currentFp.get(agent.node_id) !== configFingerprint(agent))
        changedSet.add(agent.node_id);
    }
    return changedSet;
  }, [currentStrategy, candidateStrategy]);
  if (records.length === 0) {
    return (
      <div className="ws-empty-state">
        <p>当前策略还没有演进记录。</p>
        <p style={{ fontSize: 11 }}>
          演进由证据触发：重复失败达到阈值后进入归因、候选验证与 Gate 裁决；可在后台工作台查看已有治理记录。
        </p>
      </div>
    );
  }
  const validation = d?.validations[0];
  const metricRows = validation
    ? (["tokens", "latency_seconds", "retry_count"] as const).map((key) => ({
        label: { tokens: "Token", latency_seconds: "延迟", retry_count: "Retry" }[key],
        current: validation.current_metrics[key],
        candidate: validation.candidate_metrics[key],
        goodWhenDown: true,
      }))
    : [];
  const gate = record.gate_results[0] ?? null;
  return (
    <div className="ws-evolution-view">
      <div className="ws-evo-toolbar">
        <div className="ws-evo-toolbar-left">
          <span className="ws-evo-headline">演进 {record.evolution_id}</span>
          {gate && (
            <span className="ws-tiny-badge">{human(gate.decision)}</span>
          )}
          {records.length > 1 && (
            <select
              value={selected}
              onChange={(e) => setSelected(Number(e.target.value))}
              aria-label="选择演进记录"
              style={{ fontSize: 11 }}
            >
              {records.map((r, i) => (
                <option key={r.evolution_id} value={i}>
                  {r.evolution_id}
                </option>
              ))}
            </select>
          )}
        </div>
        <div style={{ color: "var(--ws-muted)", fontSize: 11 }}>
          Current v{record.trigger.strategy.version} → Candidate{" "}
          {record.candidates[0]?.version ?? "—"}
        </div>
      </div>

      <div className="ws-evo-trigger-banner">
        <strong>为什么触发演进？</strong>
        <p>{record.trigger.reason}</p>
      </div>

      {currentStrategy && candidateStrategy && (
        <div className="ws-evo-graphs">
          <MiniStrategy
            title={`CURRENT · STRATEGY v${currentStrategy.metadata.ref.version}`}
            agents={currentStrategy.definition.agents}
            edges={currentStrategy.definition.edges}
            changed={new Set()}
          />
          <div className="ws-evo-arrow">→</div>
          <MiniStrategy
            title={`CANDIDATE · STRATEGY v${candidateStrategy.metadata.ref.version}`}
            agents={candidateStrategy.definition.agents}
            edges={candidateStrategy.definition.edges}
            changed={changed}
          />
        </div>
      )}

      <div className="ws-evo-details">
        <section className="ws-evo-section">
          <h3>Attribution & Patch</h3>
          {(d?.attributions[0]?.claims ?? []).slice(0, 3).map((claim, i) => (
            <dl className="ws-diff-row" key={i}>
              <dt>{claim.kind}</dt>
              <dd>
                {claim.target} · {claim.explanation}
              </dd>
            </dl>
          ))}
          {(d?.attributions[0]?.claims ?? []).length === 0 && (
            <dl className="ws-diff-row">
              <dt>归因</dt>
              <dd>未提供归因证据</dd>
            </dl>
          )}
          {(d?.proposals ?? []).slice(0, 2).map((proposal) => (
            <dl className="ws-diff-row" key={proposal.proposal_id}>
              <dt>Patch</dt>
              <dd>
                {proposal.operation} → {proposal.target}
              </dd>
            </dl>
          ))}
          {changed.size > 0 && (
            <button
              type="button"
              className="ws-secondary-button"
              style={{ marginTop: 8 }}
              onClick={() =>
                candidateStrategy &&
                onOpenDiff({
                  evolutionId: record.evolution_id,
                  target: [...changed][0],
                  changedFields: {
                    minus: [],
                    plus: [],
                  },
                  metrics: metricRows,
                  gate: gate
                    ? { decision: gate.decision, reasons: gate.reasons }
                    : null,
                })
              }
            >
              打开差异检查器
            </button>
          )}
        </section>

        <section className="ws-evo-section">
          <h3>Validation</h3>
          {validation ? (
            <table className="ws-metrics-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>v{validation.current.version}</th>
                  <th>v{validation.candidate.version}</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                {metricRows.map((row) => {
                  const deltaValue = delta(row.current, row.candidate);
                  return (
                    <tr key={row.label}>
                      <td>{row.label}</td>
                      <td>{row.current ?? "—"}</td>
                      <td>{row.candidate ?? "—"}</td>
                      <td
                        className={
                          deltaValue === null
                            ? ""
                            : (deltaValue < 0) === row.goodWhenDown
                              ? "ws-delta-good"
                              : "ws-delta-bad"
                        }
                      >
                        {deltaValue === null
                          ? "—"
                          : `${deltaValue > 0 ? "+" : ""}${deltaValue.toFixed(1)}%`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <p style={{ color: "var(--ws-muted)", fontSize: 11 }}>
              验证数据未提供（策略ID：{strategyId}）。
            </p>
          )}
          {gate && (
            <div
              className={`ws-gate-card ${gate.decision === "pass" ? "" : "reject"}`}
              style={{ marginTop: 12 }}
            >
              <strong>
                {gate.decision === "pass" ? "✓ Gate · " : "Gate · "}
                {human(gate.decision)}
              </strong>
              {gate.reasons.length > 0 && (
                <div
                  style={{
                    marginTop: 6,
                    color: "var(--ws-muted)",
                    fontSize: 10,
                  }}
                >
                  {gate.reasons[0]}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
