import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  Download,
  FileText,
  ListTree,
  Plus,
} from "lucide-react";
import type { Run } from "../../data/schema";
import { formatDuration, formatTokens, type AgentSpan } from "./session-data";

export function ChatView({
  detail,
  spans,
  replayToken,
  notify,
  onOpenArtifact,
  onOpenEvents,
}: {
  detail: Run;
  spans: AgentSpan[];
  replayToken: number;
  notify: (message: string) => void;
  onOpenArtifact: () => void;
  onOpenEvents: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [replayState, setReplayState] = useState<string[] | null>(null);
  const timers = useRef<number[]>([]);
  const plan = detail.plan;
  const totalDuration = spans.reduce(
    (sum, s) => (s.durationSeconds === null ? sum : sum + s.durationSeconds),
    0,
  );
  useEffect(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    if (replayToken === 0) {
      setReplayState(null);
      return;
    }
    setExpanded(true);
    const states = spans.map(() => "queued");
    setReplayState([...states]);
    spans.forEach((_, i) => {
      timers.current.push(
        window.setTimeout(() => {
          states[i] = "running";
          setReplayState([...states]);
        }, i * 800),
      );
      timers.current.push(
        window.setTimeout(() => {
          states[i] = "done";
          setReplayState([...states]);
        }, (i + 1) * 800),
      );
    });
    timers.current.push(
      window.setTimeout(() => {
        notify("执行回放完成");
        setReplayState(null);
      }, spans.length * 800 + 400),
    );
    return () => timers.current.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [replayToken]);

  const stateFor = (index: number, span: AgentSpan): string => {
    if (replayState) return replayState[index];
    if (span.status === "failed") return "failed";
    if (span.status === "running") return "running";
    return "done";
  };
  const statusText = (index: number, span: AgentSpan): string => {
    if (replayState) return replayState[index] === "running" ? "running" : replayState[index] === "queued" ? "queued" : formatDuration(span.durationSeconds);
    if (span.status === "failed") return "failed";
    if (span.tokens.input !== null || span.tokens.output !== null)
      return formatTokens(span.tokens);
    return formatDuration(span.durationSeconds);
  };
  const success = detail.evaluation.metrics.success;
  return (
    <div className="ws-chat-wrap">
      <div className="ws-transcript">
        <div className="ws-transcript-inner">
          <article className="ws-turn">
            <div className="ws-turn-meta">
              <span className="ws-avatar">你</span>
              <span>{detail.sealed_at.slice(5, 16).replace("T", " ")}</span>
            </div>
            <div className="ws-user-bubble">
              {detail.task?.instruction ?? "（该记录未提供任务说明）"}
            </div>
          </article>

          <article className="ws-turn">
            <div className="ws-turn-meta">
              <span className="ws-avatar agent">E</span>
              <span>EvoTeam</span>
            </div>

            <div
              className={`ws-process-block ${expanded ? "expanded" : ""}`}
              id="ws-process-block"
            >
              <button
                type="button"
                className="ws-process-summary-row"
                aria-expanded={expanded}
                onClick={() => setExpanded(!expanded)}
              >
                <span className="ws-process-summary-left">
                  <span className="ws-process-chevron">›</span>
                  <strong>
                    {detail.status === "completed"
                      ? "已完成"
                      : (detail.termination_reason ?? detail.status)}
                  </strong>
                  <span>
                    {spans.length} 个 Agent ·{" "}
                    {spans.reduce((n, s) => n + s.messageCount, 0)} 次协作消息
                    {spans.some((s) => s.summary !== null)
                      ? ` · ${spans.filter((s) => s.summary !== null).length} 个产物`
                      : ""}
                  </span>
                </span>
                <span className="ws-process-status">
                  {totalDuration > 0 ? `${totalDuration.toFixed(1)}s` : ""}
                </span>
              </button>
              <div className="ws-process-details">
                {spans.map((span, i) => (
                  <div className="ws-process-row" key={span.agentRunId}>
                    <span className={`ws-process-dot ${stateFor(i, span)}`} />
                    <span className="ws-process-role">{span.nodeId}</span>
                    <span className="ws-process-action">
                      {span.summary ?? span.action}
                      <small>{span.instanceId}</small>
                    </span>
                    <span className="ws-process-status">
                      {statusText(i, span)}
                    </span>
                  </div>
                ))}
                {spans.length === 0 && (
                  <p className="ws-process-status">该记录未提供执行实例。</p>
                )}
              </div>
            </div>

            <div className="ws-assistant-answer">
              {plan ? (
                <>
                  <p>
                    已完成任务执行并封存证据。当前计划覆盖{" "}
                    <strong>{plan.schedule.length} 项工作</strong>
                    ，里程碑 {plan.milestones?.length ?? 0} 个，风险 {plan.risks.length}{" "}
                    条，校验依据 {plan.validation_notes.length} 条；独立评价
                    {success === true ? "规则检查通过" : success === false ? "未通过" : "结果未提供"}
                    。
                  </p>
                  <div className="ws-inline-artifacts">
                    <button
                      type="button"
                      className="ws-artifact-chip"
                      onClick={onOpenArtifact}
                    >
                      <FileText size={12} /> 项目计划
                    </button>
                    <button
                      type="button"
                      className="ws-artifact-chip"
                      onClick={onOpenEvents}
                    >
                      <ListTree size={12} /> 执行事件
                    </button>
                    <a
                      className="ws-artifact-chip"
                      style={{ textDecoration: "none" }}
                      href={`/v1/runs/${encodeURIComponent(detail.run_id)}/export`}
                      download
                    >
                      <Download size={12} /> 证据导出
                    </a>
                  </div>
                  <p>
                    过程细节可在“轨迹”查看逐事件因果；团队组织与交接在“团队”视图展开。
                  </p>
                  <div className="ws-source-row">
                    已封存 {detail.sealed_at.slice(0, 19).replace("T", " ")} · Strategy
                    v{detail.strategy.version} ·{" "}
                    {success === true
                      ? "Validation passed"
                      : success === false
                        ? "Validation failed"
                        : "Validation unknown"}
                  </div>
                </>
              ) : (
                <p>
                  本次执行未产生完整计划产物
                  {detail.termination_reason
                    ? `，终止原因：${detail.termination_reason}。`
                    : "。"}
                  可在“轨迹”查看逐事件证据。
                </p>
              )}
            </div>
          </article>
        </div>
      </div>

      <div className="ws-composer-wrap">
        <div className="ws-composer">
          <textarea
            placeholder="发送消息或分配任务… / 调用指令，@ 文件或知识"
            aria-label="任务输入"
            onClick={() => notify("实时提交依赖执行作业服务（契约 F1/F2），当前会话为只读回放")}
            readOnly
          />
          <div className="ws-composer-footer">
            <div className="ws-composer-tools">
              {["＋", "Agent ▾", "标准权限 ▾", "@ 上下文"].map((label) => (
                <button
                  key={label}
                  type="button"
                  className="ws-composer-pill"
                  onClick={() => notify("该能力随实时执行服务（F1/F2）开放")}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="ws-composer-tools">
              <button
                type="button"
                className="ws-composer-pill"
                onClick={() => notify("模型绑定在服务端配置，不在页面展示密钥")}
              >
                模型 ▾
              </button>
              <button
                type="button"
                className="ws-send-button"
                aria-label="发送"
                onClick={() => notify("实时提交依赖执行作业服务（契约 F1/F2）")}
              >
                <ArrowUp size={15} />
              </button>
            </div>
          </div>
        </div>
        <p className="ws-source-row" style={{ textAlign: "center" }}>
          <Plus size={9} style={{ verticalAlign: "middle" }} /> 运行中用户输入仅作为展示层注记插入对话流，不参与本次执行——该能力随实时执行服务交付。
        </p>
      </div>
    </div>
  );
}
