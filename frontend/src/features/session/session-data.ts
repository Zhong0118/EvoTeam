import type { Run, TraceEvent } from "../../data/schema";
import { buildAgentRuns, type AgentRunRow } from "../runtime/projection";

// 会话工作区的单一数据装配点：chat / trace / team / evolution 全部从这里取数。

export interface AgentSpan {
  agentRunId: string;
  nodeId: string;
  instanceId: string;
  status: AgentRunRow["status"];
  summary: string | null;
  action: string;
  startSeq: number;
  endSeq: number;
  startedAt: string | null;
  endedAt: string | null;
  durationSeconds: number | null;
  tokens: { input: number | null; output: number | null };
  messageCount: number;
}

const timestamp = (value: string): number | null => {
  const t = Date.parse(value);
  return Number.isNaN(t) ? null : t;
};

export function agentDurationSeconds(span: {
  startedAt: string | null;
  endedAt: string | null;
}): number | null {
  const from = span.startedAt ? timestamp(span.startedAt) : null;
  const to = span.endedAt ? timestamp(span.endedAt) : null;
  if (from === null || to === null || to < from) return null;
  return (to - from) / 1000;
}

export function formatDuration(seconds: number | null): string {
  return seconds === null ? "—" : `${seconds.toFixed(1)}s`;
}

export function formatTokens(tokens: {
  input: number | null;
  output: number | null;
}): string {
  const total =
    tokens.input === null && tokens.output === null
      ? null
      : (tokens.input ?? 0) + (tokens.output ?? 0);
  return total === null ? "—" : `${(total / 1000).toFixed(1)}k`;
}

export function buildAgentSpans(
  detail: Run,
  events: TraceEvent[],
): AgentSpan[] {
  const agents = buildAgentRuns(detail, events);
  const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
  return agents.map((agent) => {
    const own = ordered.filter((e) => e.instance_id === agent.instanceId);
    const startSeq = own[0]?.sequence ?? -1;
    const endSeq = own[own.length - 1]?.sequence ?? startSeq;
    const completed = own.find((e) => e.event_type === "agent_completed");
    return {
      agentRunId: agent.agentRunId,
      nodeId: agent.nodeId,
      instanceId: agent.instanceId,
      status: agent.status,
      summary: summarizeSpanOutput(agent.output),
      action:
        agent.step ??
        (completed ? "已交付结果" : (own[0]?.event_type ?? "等待上游")),
      startSeq,
      endSeq,
      startedAt: agent.startedAt,
      endedAt: agent.endedAt,
      durationSeconds: agentDurationSeconds(agent),
      tokens: {
        input: agentTokens(detail, agent.instanceId, "input"),
        output: agentTokens(detail, agent.instanceId, "output"),
      },
      messageCount: agent.messages.length,
    };
  });
}

function agentTokens(
  detail: Run,
  instanceId: string,
  kind: "input" | "output",
): number | null {
  const instance = (detail.instances ?? []).find(
    (i) => i.instance_id === instanceId,
  );
  if (!instance) return null;
  return kind === "input"
    ? (instance.input_tokens ?? null)
    : (instance.output_tokens ?? null);
}

function summarizeSpanOutput(output: unknown): string | null {
  if (output === null || typeof output !== "object") return null;
  const data = output as Record<string, unknown>;
  if (typeof data.summary === "string") return data.summary;
  if (Array.isArray(data.schedule))
    return `生成排期 ${data.schedule.length} 项工作`;
  if (typeof data.passed === "boolean")
    return data.passed ? "审查通过" : "审查未通过";
  return null;
}

export interface TraceRow {
  key: string;
  sequence: number;
  track: "input" | "agent" | "message" | "system";
  badge: string;
  name: string;
  summary: string;
  duration: number | null;
  tokens: string;
  eventId: string;
}

const EVENT_BADGE: Record<string, TraceRow["track"]> = {
  task_created: "input",
  team_created: "input",
  agent_started: "agent",
  agent_completed: "agent",
  agent_failed: "agent",
  agent_message: "message",
  run_finished: "system",
  evaluation_completed: "system",
  run_sealed: "system",
};
const BADGE_LABEL: Record<TraceRow["track"], string> = {
  input: "输入",
  agent: "Agent",
  message: "消息",
  system: "系统",
};
const EVENT_NAME: Record<string, string> = {
  task_created: "提交任务",
  team_created: "组装团队",
  agent_started: "开始执行",
  agent_completed: "交付结果",
  agent_failed: "执行失败",
  agent_message: "协作消息",
  run_finished: "运行结束",
  evaluation_completed: "独立评价",
  run_sealed: "证据封存",
};

export function buildTraceRows(
  detail: Run,
  events: TraceEvent[],
): TraceRow[] {
  const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
  let previous: number | null = null;
  return ordered.map((event) => {
    const at = timestamp(event.timestamp);
    const duration =
      previous !== null && at !== null && at >= previous ? (at - previous) / 1000 : null;
    previous = at ?? previous;
    const track = EVENT_BADGE[event.event_type] ?? "system";
    const instance =
      event.instance_id && detail.instances
        ? detail.instances.find((i) => i.instance_id === event.instance_id)
        : undefined;
    const tokens = instance
      ? formatTokens({
          input: instance.input_tokens ?? null,
          output: instance.output_tokens ?? null,
        })
      : "—";
    const outputSummary =
      event.output !== null && event.output !== undefined
        ? summarizeSpanOutput(event.output)
        : null;
    return {
      key: event.event_id,
      sequence: event.sequence,
      track,
      badge: BADGE_LABEL[track],
      name: `${EVENT_NAME[event.event_type] ?? event.event_type}${
        event.node_id ? ` · ${event.node_id}` : ""
      }`,
      summary:
        outputSummary ??
        (event.event_type === "agent_message"
          ? "产物沿配置连边交付下游"
          : (event.instance_id ?? "—")),
      duration,
      tokens: event.event_type === "agent_completed" ? tokens : "—",
      eventId: event.event_id,
    };
  });
}

export function buildTimeline(
  detail: Run,
  events: TraceEvent[],
  spans: AgentSpan[],
): {
  track: TraceRow["track"];
  left: number;
  width: number;
  label: string;
  eventId: string | null;
}[] {
  const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
  const maxSeq = Math.max(1, ordered[ordered.length - 1]?.sequence ?? 1);
  const at = (seq: number) => (Math.max(0, seq) / maxSeq) * 100;
  const bars: ReturnType<typeof buildTimeline> = [];
  for (const event of ordered) {
    const track = EVENT_BADGE[event.event_type] ?? "system";
    if (track === "agent") continue;
    bars.push({
      track,
      left: at(event.sequence),
      width: Math.max(1.6, 100 / (maxSeq + 1)),
      label: EVENT_NAME[event.event_type] ?? event.event_type,
      eventId: event.event_id,
    });
  }
  for (const span of spans) {
    if (span.startSeq < 0) continue;
    bars.push({
      track: "agent",
      left: at(span.startSeq),
      width: Math.max(1.6, at(span.endSeq) - at(span.startSeq)),
      label: `${span.nodeId} · ${span.summary ?? span.action}`,
      eventId: null,
    });
  }
  return bars;
}

export function sessionSub(detail: Run | null): string {
  if (!detail) return "加载中…";
  const agents = detail.instances?.length ?? 0;
  const state =
    detail.status === "completed"
      ? "已完成"
      : detail.status === "failed"
        ? "运行失败"
        : detail.status === "timed_out"
          ? "已超时"
          : detail.status;
  return `${agents} Agents · ${state}`;
}
