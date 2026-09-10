import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  RefreshCw,
  Filter,
  Search,
  Workflow,
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
  SourceNote,
  human,
  number,
  time,
  EvidenceHint,
} from "../components/evidence/common";
import { defaultStrategy, useEvidence } from "../data/client";
import { pageSchema, runSchema } from "../data/schema";
const schema = pageSchema(runSchema);
export function Runs() {
  const [params, setParams] = useSearchParams();
  const strategy = params.get("strategy_id") ?? defaultStrategy;
  const purpose = params.get("purpose") || "";
  const cursor = params.get("cursor");
  const path = strategy
    ? `/runs?${new URLSearchParams({ strategy_id: strategy, ...(purpose ? { purpose } : {}), ...(cursor ? { cursor } : {}), limit: "20" })}`
    : null;
  const query = useEvidence(path, schema);
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params);
    next.delete("cursor");
    next.delete("prev");
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }
  return (
    <>
      <PageTitle
        title="运行记录"
        description="从任务结果出发，追溯团队的每一步执行。"
        actions={
          <Button onClick={query.refresh} disabled={!strategy}>
            <RefreshCw size={15} />
            刷新记录
          </Button>
        }
      />
      <div className="filter-bar">
        <div className="filter-tabs" aria-label="用途筛选">
          {[
            ["", "全部用途"],
            ["online", "线上任务"],
            ["validation", "隔离验证"],
            ["final_test", "最终测试"],
            ["diagnostic", "诊断"],
          ].map(([v, label]) => (
            <button
              key={v}
              aria-pressed={purpose === v}
              className={purpose === v ? "selected" : ""}
              onClick={() => filter("purpose", v)}
            >
              {label}
            </button>
          ))}
        </div>
        <form
          className="strategy-search"
          onSubmit={(e) => {
            e.preventDefault();
            filter(
              "strategy_id",
              String(new FormData(e.currentTarget).get("strategy") || ""),
            );
          }}
        >
          <Search size={15} />
          <input
            key={strategy}
            aria-label="策略 ID"
            name="strategy"
            placeholder="输入策略 ID"
            defaultValue={strategy}
          />
          <Button type="submit" variant="default">
            查询
          </Button>
        </form>
      </div>
      <div className="guide-strip">
        <div className="guide-icon">
          <Workflow size={23} />
        </div>
        <div>
          <strong>一次运行，一条完整证据链</strong>
          <p>
            任务与计划 <ArrowRight size={12} /> 团队与 Trace{" "}
            <ArrowRight size={12} /> 独立评价 <ArrowRight size={12} />{" "}
            版本与演进
          </p>
        </div>
        <Badge>
          <CircleCheck size={12} /> 只读工作台
        </Badge>
      </div>
      {!strategy ? (
        <Empty title="选择一个策略开始浏览">在上方输入已登记的策略 ID。</Empty>
      ) : (
        <>
          <QueryState {...query} retry={query.refresh} />
          {query.value && (
            <>
              <Panel
                title="已封存的运行"
                aside={
                  <span className="tiny">
                    <Filter size={13} /> 当前页 {query.value.data.items.length}{" "}
                    条 · 每页最多 20 条
                  </span>
                }
              >
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Run / 任务</th>
                        <th>策略</th>
                        <th>用途</th>
                        <th>运行状态</th>
                        <th>评价</th>
                        <th>Token</th>
                        <th>耗时</th>
                        <th>封存时间</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {query.value.data.items.map((run) => (
                        <tr key={run.run_id}>
                          <td>
                            <CopyId id={run.run_id} />
                            <div className="tiny">项目规划 · {run.task_id}</div>
                          </td>
                          <td>
                            <Link
                              className="version-link"
                              to={`/strategies/${encodeURIComponent(run.strategy.strategy_id)}`}
                            >
                              v{run.strategy.version}
                            </Link>
                          </td>
                          <td>
                            <Badge value={run.purpose} />
                          </td>
                          <td>
                            <Badge value={run.status} />
                          </td>
                          <td>
                            <span
                              className={
                                run.evaluation.metrics.success === false
                                  ? "error-text"
                                  : ""
                              }
                            >
                              {run.evaluation.metrics.success == null
                                ? "未提供"
                                : run.evaluation.metrics.success
                                  ? "通过"
                                  : "未通过"}
                            </span>
                          </td>
                          <td className="mono">
                            {number(run.evaluation.metrics.tokens)}
                          </td>
                          <td className="mono">
                            {number(
                              run.evaluation.metrics.latency_seconds,
                              " s",
                            )}
                          </td>
                          <td className="tiny nowrap">{time(run.sealed_at)}</td>
                          <td>
                            <Link
                              className="view-link"
                              to={`/runs/${encodeURIComponent(run.run_id)}`}
                              aria-label={`查看 ${run.run_id}`}
                            >
                              查看 <ArrowRight size={14} />
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {query.value.data.items.length === 0 && (
                  <Empty>
                    <button
                      className="text-button"
                      onClick={() => filter("purpose", "")}
                    >
                      清除用途筛选
                    </button>
                  </Empty>
                )}
                <div className="pagination">
                  <span className="muted">
                    {purpose ? human(purpose) : "全部用途"} ·
                    不合并不同用途的指标
                  </span>
                  <div className="actions">
                    <Button
                      disabled={!cursor}
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
                      onClick={() => {
                        const n = new URLSearchParams(params);
                        n.append("prev", cursor || "");
                        n.set("cursor", query.value!.data.next_cursor!);
                        setParams(n);
                      }}
                    >
                      下一页 <ArrowRight size={14} />
                    </Button>
                  </div>
                </div>
              </Panel>
              <SourceNote envelope={query.value} />
            </>
          )}
        </>
      )}
      <EvidenceHint />
    </>
  );
}
