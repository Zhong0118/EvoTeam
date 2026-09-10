import { useEffect, useRef, useState } from "react";
import { ChevronRight, CornerDownRight, RotateCcw } from "lucide-react";
import { Raw, time } from "./common";
import type { TraceEvent } from "../../data/schema";

const ACTION: Record<string, string> = {
  task_created: "接收任务",
  team_created: "组装团队",
  agent_started: "开始执行",
  agent_completed: "交付结果",
  agent_failed: "执行失败",
  agent_message: "传递消息",
  tool_called: "调用工具",
  tool_result: "工具结果",
  run_finished: "运行结束",
  evaluation_completed: "独立评价完成",
  run_sealed: "证据封存",
};

// 面向轨道卡片的可读摘要；只描述已保存产物，不推算结论。
export function summarizeOutput(output: unknown): string | null {
  if (output === null || typeof output !== "object") return null;
  const data = output as Record<string, unknown>;
  if (typeof data.summary === "string") return data.summary;
  if (Array.isArray(data.schedule)) {
    const risks = Array.isArray(data.risks) ? data.risks.length : null;
    const milestones = Array.isArray(data.milestones)
      ? data.milestones.length
      : null;
    return [
      `排期 ${data.schedule.length} 项工作`,
      milestones === null ? null : `覆盖 ${milestones} 个里程碑`,
      risks === null ? null : `风险 ${risks} 条`,
    ]
      .filter((part): part is string => part !== null)
      .join(" · ");
  }
  if (typeof data.passed === "boolean") {
    const issues = Array.isArray(data.issues) ? data.issues.length : 0;
    return data.passed ? "审查通过，未发现问题" : `审查未通过 · ${issues} 个问题`;
  }
  if (typeof data.success === "boolean") {
    const errors =
      typeof data.hard_constraint_errors === "number"
        ? data.hard_constraint_errors
        : null;
    return [
      data.success ? "规则检查通过" : "规则检查未通过",
      errors === null ? null : `${errors} 个硬约束错误`,
    ]
      .filter((part): part is string => part !== null)
      .join(" · ");
  }
  return null;
}

function stepKind(event: TraceEvent): "agent" | "system" | "flow" {
  if (event.event_type.startsWith("agent_")) return "agent";
  if (event.event_type === "agent_message") return "flow";
  return "system";
}

function TrackCard({
  event,
  active,
  last,
  onSelect,
}: {
  event: TraceEvent;
  active: boolean;
  last: boolean;
  onSelect: (event: TraceEvent) => void;
}) {
  const kind = stepKind(event);
  const failed = event.event_type === "agent_failed";
  const summary = summarizeOutput(event.output);
  const config = event.config as Record<string, unknown> | null | undefined;
  const nodes = Array.isArray(config?.enabled_nodes)
    ? (config.enabled_nodes as string[])
    : null;
  return (
    <div className={`track-rail ${last ? "last" : ""}`}>
      <span
        className={`track-dot ${event.node_state ?? "system"} ${
          active && event.node_state === "running" ? "pulse" : ""
        } ${failed ? "failed" : ""}`}
      />
      <button
        type="button"
        className={`track-step event-row ${active ? "selected" : ""} ${
          failed ? "failed" : ""
        } ${kind === "system" ? "system" : ""}`}
        onClick={() => onSelect(event)}
      >
        <span className="track-head">
          {event.node_id && (
            <span className="track-node">{event.node_id.toUpperCase()}</span>
          )}
          <strong>{ACTION[event.event_type] ?? event.event_type}</strong>
          <span className="track-time">{time(event.timestamp)}</span>
        </span>
        {event.instance_id && (
          <small className="track-instance">{event.instance_id}</small>
        )}
        {nodes && (
          <span className="track-chips">
            {nodes.map((node) => (
              <span className="chip" key={node}>
                {node}
              </span>
            ))}
            {nodes.length === 0 && <small>未提供执行计划</small>}
          </span>
        )}
        {summary && <p className="track-summary">{summary}</p>}
        {event.event_type === "agent_message" && (
          <span className="track-flow">
            <CornerDownRight size={13} /> 产物沿配置连边传递给下游节点
          </span>
        )}
        {event.caused_by.length > 0 && (
          <small className="track-caused">
            承接 {event.caused_by[0].slice(0, 8)}…
          </small>
        )}
        {event.output !== null && event.output !== undefined && (
          <Raw value={event.output} title="展开结构化输出" />
        )}
        <ChevronRight size={13} className="track-open" />
      </button>
    </div>
  );
}

export function RunTrack({
  events,
  activeIndex,
  streaming,
  onSelect,
}: {
  events: TraceEvent[];
  activeIndex: number;
  streaming: boolean;
  onSelect: (event: TraceEvent) => void;
}) {
  const visible = streaming ? events.slice(0, activeIndex + 1) : events;
  const box = useRef<HTMLDivElement>(null);
  const [follow, setFollow] = useState(true);
  useEffect(() => {
    if (!follow) return;
    const node = box.current;
    if (node && typeof node.scrollTo === "function")
      node.scrollTo({
        top: node.scrollHeight,
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
      });
  }, [visible.length, activeIndex, follow]);
  return (
    <div className="track-wrap">
      <div
        ref={box}
        className="track"
        onScroll={(e) => {
          const el = e.currentTarget;
          const bottom =
            el.scrollHeight - el.scrollTop - el.clientHeight < 48;
          if (!bottom && follow) setFollow(false);
          if (bottom && !follow) setFollow(true);
        }}
      >
        {visible.map((event, i) => (
          <TrackCard
            key={event.event_id}
            event={event}
            active={i === activeIndex}
            last={i === visible.length - 1}
            onSelect={onSelect}
          />
        ))}
        {streaming && (
          <div className="track-streaming">
            <span className="track-dot running pulse" />
            <small>执行中…</small>
          </div>
        )}
      </div>
      {!follow && (
        <button
          type="button"
          className="track-jump"
          onClick={() => {
            setFollow(true);
            const node = box.current;
            if (node && typeof node.scrollTo === "function")
              node.scrollTo({
                top: node.scrollHeight,
                behavior: "smooth",
              });
          }}
        >
          <RotateCcw size={12} /> 回到最新
        </button>
      )}
    </div>
  );
}
