import type { Run, TraceEvent } from "../../data/schema";

// V2 规范 §22/§23：Run/instance 数据的前端投影，session 内所有视图共享。
// agentRunId 短期由 run_id + instance_id 组合，后端提供稳定 ID 后切换。

export type AgentRunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "timed_out";

export interface AgentRunRow {
  agentRunId: string;
  runId: string;
  instanceId: string;
  nodeId: string;
  status: AgentRunStatus;
  step: string | null;
  output: unknown;
  messages: { from: string | null; to: string; sourceEventIds: string[] }[];
  startedAt: string | null;
  endedAt: string | null;
}

const STATUS_BY_STATE: Record<string, AgentRunStatus> = {
  created: "queued",
  running: "running",
  completed: "completed",
  failed: "failed",
  cancelled: "cancelled",
  timed_out: "timed_out",
};

export function buildAgentRuns(
  detail: Run,
  events: TraceEvent[],
): AgentRunRow[] {
  const rows = new Map<string, AgentRunRow>();
  for (const ins of detail.instances ?? []) {
    rows.set(ins.instance_id, {
      agentRunId: `${detail.run_id}:${ins.instance_id}`,
      runId: detail.run_id,
      instanceId: ins.instance_id,
      nodeId: ins.node_id,
      status: STATUS_BY_STATE[ins.state] ?? "queued",
      step: null,
      output: ins.output ?? null,
      messages: ins.messages.map((m) => ({
        from: m.sender_node_id,
        to: m.recipient_node_id,
        sourceEventIds: m.source_event_ids,
      })),
      startedAt: null,
      endedAt: null,
    });
  }
  const orderedEvents = [...events].sort((a, b) => a.sequence - b.sequence);
  for (const event of orderedEvents) {
    if (!event.instance_id) continue;
    const row = rows.get(event.instance_id);
    if (!row) continue;
    if (event.event_type === "agent_started") {
      row.startedAt = event.timestamp;
      row.step = "执行中";
    } else if (event.event_type === "agent_completed") {
      row.endedAt = event.timestamp;
      row.step = "已交付结果";
    } else if (event.event_type === "agent_failed") {
      row.endedAt = event.timestamp;
      row.step = "执行失败";
    } else if (event.event_type === "agent_message") {
      row.step = "产物沿连边交付下游";
    }
    if (event.output !== null && event.output !== undefined) row.output = event.output;
  }
  return [...rows.values()];
}

export interface SessionConversation {
  instruction: string | null;
  status: string;
  sealedAt: string;
  terminationReason: string | null;
  evaluation: Run["evaluation"] | null;
  plan: Run["plan"];
  agents: AgentRunRow[];
  counts: { agents: number; messages: number; artifacts: number };
}

export function buildConversation(
  detail: Run,
  events: TraceEvent[],
): SessionConversation {
  const agents = buildAgentRuns(detail, events);
  return {
    instruction: detail.task?.instruction ?? null,
    status: detail.status,
    sealedAt: detail.sealed_at,
    terminationReason: detail.termination_reason ?? null,
    evaluation: detail.evaluation,
    plan: detail.plan ?? null,
    agents,
    counts: {
      agents: agents.length,
      messages: agents.reduce((n, a) => n + a.messages.length, 0),
      artifacts: agents.filter((a) => a.output !== null && a.output !== undefined)
        .length,
    },
  };
}

export interface CollaborationItem {
  key: string;
  nodeId: string | null;
  text: string;
  detail: string | null;
  timestamp: string;
  kind: "handoff" | "step";
}

export function buildCollaboration(events: TraceEvent[]): CollaborationItem[] {
  const ACTION: Record<string, string> = {
    agent_started: "开始执行",
    agent_completed: "已交付结果",
    agent_failed: "执行失败",
    agent_message: "产物已发送给下游",
  };
  return [...events]
    .sort((a, b) => a.sequence - b.sequence)
    .filter((e) => e.event_type.startsWith("agent_"))
    .map((e) => ({
      key: e.event_id,
      nodeId: e.node_id,
      text: ACTION[e.event_type] ?? e.event_type,
      detail:
        e.event_type === "agent_message"
          ? e.node_id
            ? `@${e.node_id} · 来源 ${e.caused_by[0]?.slice(0, 8) ?? "未知"}`
            : null
          : (e.instance_id ?? null),
      timestamp: e.timestamp,
      kind: e.event_type === "agent_message" ? "handoff" : "step",
    }));
}
