import { StrategyDiff } from "../components/evidence/strategy-diff";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Layers3, ArrowRight } from "lucide-react";
import {
  Badge,
  Empty,
  PageTitle,
  Panel,
  QueryState,
  Raw,
  SourceNote,
} from "../components/evidence/common";
import { useEvidence } from "../data/client";
import { versionsSchema } from "../data/schema";
export function Strategies() {
  const { strategyId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const query = useEvidence(
    strategyId
      ? `/strategies/${encodeURIComponent(strategyId)}/versions`
      : null,
    versionsSchema,
  );
  const [compare, setCompare] = useState<number[]>([]);
  const d = query.value?.data;
  const selected = d?.items.find(
    (s) =>
      s.metadata.ref.version ===
      Number(
        params.get("version") ??
          d.current?.version ??
          d.items[0]?.metadata.ref.version,
      ),
  );
  const formal =
    d?.items.filter((s) =>
      ["current", "stable", "retired", "rolled_back"].includes(
        s.metadata.status,
      ),
    ) ?? [];
  const candidates = d?.items.filter((s) => !formal.includes(s)) ?? [];
  return (
    <>
      <PageTitle
        title="版本与指标"
        description={
          strategyId
            ? `Strategy · ${strategyId}`
            : "选择一个策略，查看正式版本与隔离候选。"
        }
      />
      {!strategyId ? (
        <Empty title="尚未选择策略">
          <Link to="/dashboard/runs">从运行记录选择策略 →</Link>
        </Empty>
      ) : (
        <>
          <QueryState {...query} retry={query.refresh} />
          {d && (
            <>
              <Panel
                title="正式版本"
                aside={
                  <span className="tiny">
                    单条版本链 · Current 以服务引用为准
                  </span>
                }
              >
                <div className="version-line">
                  {formal.map((s, i) => (
                    <div key={s.metadata.ref.version} className="version-step">
                      <button
                        className={`version-card ${selected === s ? "selected" : ""}`}
                        onClick={() =>
                          setParams({ version: String(s.metadata.ref.version) })
                        }
                      >
                        <Layers3 size={20} />
                        <strong>v{s.metadata.ref.version}</strong>
                        <Badge value={s.metadata.status}>
                          {d.current?.version === s.metadata.ref.version
                            ? "Current · 当前服务"
                            : undefined}
                        </Badge>
                        <small>代次 {s.metadata.generation}</small>
                      </button>
                      {i < formal.length - 1 && <ArrowRight size={20} />}
                    </div>
                  ))}
                </div>
                {!formal.length && <Empty title="尚无正式服务版本" />}
                <p className="tiny">
                  排列依据版本标识；状态来自存储，未提供服务时间的版本不推测服务日期。
                </p>
              </Panel>
              <div className="columns section-gap">
                <Panel title="版本详情">
                  {selected ? (
                    <>
                      <div className="record-strip">
                        <Badge>v{selected.metadata.ref.version}</Badge>
                        <Badge value={selected.metadata.status} />
                      </div>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>节点</th>
                              <th>Role</th>
                              <th>Prompt</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selected.definition.agents.map((a) => (
                              <tr key={a.node_id}>
                                <td>{a.node_id}</td>
                                <td>{a.role}</td>
                                <td>
                                  {a.prompt_ref.id}@{a.prompt_ref.version}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <Raw
                        value={selected.definition}
                        title="查看 Tool / Skill 引用和连边"
                      />
                    </>
                  ) : (
                    <Empty title="选择一个版本" />
                  )}
                </Panel>
                <Panel title="指标范围">
                  <p>当前版本接口未提供全量汇总指标。</p>
                  <p className="muted">
                    成功数、Token
                    与耗时请在具体运行或验证记录中查看。列表分页数据不能作为全局统计。
                  </p>
                  <Link
                    className="view-link"
                    to={`/dashboard/evolutions?strategy_id=${encodeURIComponent(strategyId)}`}
                  >
                    查看验证比较 <ArrowRight size={14} />
                  </Link>
                </Panel>
              </div>
              <Panel
                title="候选比较区"
                aside={<Badge value="candidate">隔离验证</Badge>}
              >
                <div className="candidate-grid">
                  {candidates.map((s) => (
                    <div
                      className="candidate-card"
                      key={s.metadata.ref.version}
                    >
                      <button
                        className="text-button"
                        onClick={() =>
                          setParams({ version: String(s.metadata.ref.version) })
                        }
                      >
                        Candidate v{s.metadata.ref.version}
                      </button>
                      <Badge value={s.metadata.status} />
                      <p className="tiny">
                        来源 v{s.metadata.parent?.version ?? "未提供"}
                      </p>
                    </div>
                  ))}
                </div>
                {!candidates.length && (
                  <p className="muted">没有已登记候选。</p>
                )}
                <p>选择最多两个已登记版本，查看配置差异：</p>
                <div className="actions">
                  {d.items.map((s) => (
                    <label className="check-label" key={s.metadata.ref.version}>
                      <input
                        type="checkbox"
                        checked={compare.includes(s.metadata.ref.version)}
                        disabled={
                          compare.length === 2 &&
                          !compare.includes(s.metadata.ref.version)
                        }
                        onChange={(e) =>
                          setCompare((prev) =>
                            e.target.checked
                              ? [...prev, s.metadata.ref.version]
                              : prev.filter(
                                  (v) => v !== s.metadata.ref.version,
                                ),
                          )
                        }
                      />
                      v{s.metadata.ref.version}
                    </label>
                  ))}
                </div>
                {compare.length === 2 && (
                  <div className="comparison">
                    <StrategyDiff
                      left={d.items.find(
                        (s) => s.metadata.ref.version === compare[0],
                      )!}
                      right={d.items.find(
                        (s) => s.metadata.ref.version === compare[1],
                      )!}
                    />
                    <p className="tiny">
                      这里只比较配置，不推算收益。模型、用途或预算不同的运行不能直接合并评价。
                    </p>
                  </div>
                )}
              </Panel>
              <SourceNote envelope={query.value!} />
            </>
          )}
        </>
      )}
    </>
  );
}
