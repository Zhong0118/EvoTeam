import { useMemo, useState } from "react";
import type { Run, TraceEvent } from "../../data/schema";
import {
  buildTimeline,
  buildTraceRows,
  formatDuration,
} from "./session-data";

const TRACK_LABELS: Record<string, string> = {
  input: "输入",
  agent: "Agent",
  message: "消息",
  system: "系统",
};

export function TraceView({
  detail,
  events,
  selectedEventId,
  traceFilter,
  onInspectEvent,
}: {
  detail: Run;
  events: TraceEvent[];
  selectedEventId: string | null;
  traceFilter: string;
  onInspectEvent: (event: TraceEvent) => void;
}) {
  const rows = useMemo(() => buildTraceRows(detail, events), [detail, events]);
  const spans = useMemo(
    () => buildTimeline(detail, events, []),
    // buildTimeline needs spans for agent bars; recompute inline below instead.
    [detail, events],
  );
  void spans;
  const [search, setSearch] = useState("");
  const filtered = rows.filter((row) =>
    `${row.name} ${row.summary}`.toLowerCase().includes(traceFilter.toLowerCase() || search.toLowerCase()),
  );
  const bars = useMemo(
    () => buildTimeline(detail, events, []),
    [detail, events],
  );
  const agentBars = useMemo(() => {
    // Agent spans from events: group by instance, first/last sequence.
    const byInstance = new Map<string, { start: number; end: number }>();
    const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
    for (const e of ordered) {
      if (!e.instance_id) continue;
      const span = byInstance.get(e.instance_id) ?? {
        start: e.sequence,
        end: e.sequence,
      };
      span.start = Math.min(span.start, e.sequence);
      span.end = Math.max(span.end, e.sequence);
      byInstance.set(e.instance_id, span);
    }
    const maxSeq = Math.max(1, ordered[ordered.length - 1]?.sequence ?? 1);
    return [...byInstance.entries()].map(([instanceId, span]) => ({
      track: "agent" as const,
      left: (Math.max(0, span.start) / maxSeq) * 100,
      width: Math.max(
        1.6,
        ((span.end - span.start) / maxSeq) * 100,
      ),
      label: `${instanceId}`,
      eventId: null,
      instanceId,
    }));
  }, [events]);
  return (
    <div className="ws-trace-view">
      <div className="ws-trace-toolbar">
        <div className="ws-trace-title-group">
          <div
            style={{
              display: "flex",
              border: "1px solid var(--ws-line)",
              borderRadius: 8,
              padding: 2,
              background: "#fafafa",
            }}
          >
            {["时长", "轮次", "调用"].map((label, i) => (
              <button
                key={label}
                type="button"
                style={{
                  border: 0,
                  background: i === 0 ? "white" : "transparent",
                  padding: "5px 8px",
                  borderRadius: 6,
                  cursor: i === 0 ? "default" : "pointer",
                  fontSize: 11,
                  color: i === 0 ? "var(--ws-text)" : "var(--ws-muted)",
                  boxShadow: i === 0 ? "0 1px 2px rgba(0,0,0,.05)" : "none",
                }}
                onClick={() => {
                  if (i !== 0) {
                    // 轮次/调用聚合随执行服务数据补齐开放
                  }
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="ws-state-pill">
            <i />
            {detail.status === "completed"
              ? "Session complete"
              : detail.status}
          </span>
        </div>
        <input
          className="ws-search-input"
          placeholder="⌕ 搜索轨迹"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="搜索轨迹"
        />
      </div>

      <div className="ws-timeline-overview">
        <div className="ws-timeline-labels">
          <span>输入</span>
          <span>Agent</span>
          <span>消息</span>
          <span>系统</span>
        </div>
        <div className="ws-timeline-track">
          {(["input", "agent", "message", "system"] as const).map((track) => (
            <div className="ws-timeline-row" key={track}>
              {(track === "agent" ? agentBars : bars)
                .filter((bar) => bar.track === track)
                .map((bar, i) => (
                  <span
                    key={`${track}-${i}`}
                    className={`ws-timeline-bar ${bar.track}`}
                    style={{ left: `${bar.left}%`, width: `${bar.width}%` }}
                    title={bar.label}
                    onClick={() => {
                      if (bar.eventId) {
                        const event = events.find(
                          (e) => e.event_id === bar.eventId,
                        );
                        if (event) onInspectEvent(event);
                      } else if ("instanceId" in bar && bar.instanceId) {
                        setSearch(String(bar.instanceId));
                      }
                    }}
                  />
                ))}
            </div>
          ))}
        </div>
      </div>

      <table className="ws-trace-table">
        <thead>
          <tr>
            <th>#</th>
            <th>类型</th>
            <th>记录</th>
            <th>摘要</th>
            <th style={{ textAlign: "right" }}>间隔</th>
            <th style={{ textAlign: "right" }}>Token</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((row) => (
            <tr
              key={row.key}
              className={row.eventId === selectedEventId ? "selected" : ""}
              onClick={() => {
                const event = events.find((e) => e.event_id === row.eventId);
                if (event) onInspectEvent(event);
              }}
            >
              <td className="ws-trace-index">
                {String(row.sequence).padStart(2, "0")}
              </td>
              <td>
                <span className={`ws-trace-badge ${row.track}`}>
                  {row.badge}
                </span>
              </td>
              <td className="ws-trace-kind">{row.name}</td>
              <td>{row.summary}</td>
              <td className="ws-trace-duration">
                {formatDuration(row.duration)}
              </td>
              <td className="ws-trace-token">{row.tokens}</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr>
              <td colSpan={6} style={{ color: "var(--ws-muted)" }}>
                没有匹配的轨迹记录。
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <p className="ws-source-row">
        “间隔”为相邻事件时间戳差值（示意节奏，非实际模型耗时）；Token 为已提供的实例用量，未知显示 —。
      </p>
    </div>
  );
}

export { TRACK_LABELS };
