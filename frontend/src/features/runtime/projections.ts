/* Session projections — the single parse point required by V3 §20. Chat,
   the Live Execution Graph and every Inspector consume these outputs; no
   view may re-read raw events on its own. Pure functions, unit-tested. */
import type { AgentEvent, AgentRun, ExecutionGraphEdge, ExecutionGraphNode } from "./types";
import { sessionGraph, sessionRunId } from "../../fixtures/session-events";

export interface ProjectedSession {
  agentRuns: AgentRun[];
  agentRunById: Map<string, AgentRun>;
  handoffs: { from: string; to: string; summary?: string; sequence: number }[];
  reworks: { agentRunId: string; summary?: string }[];
  evaluation?: AgentEvent;
  finished: boolean;
}

const runKey = (instanceId: string) => `${sessionRunId}:${instanceId}`;

export function projectSession(events: AgentEvent[]): ProjectedSession {
  const byId = new Map<string, AgentRun>();
  const order: string[] = [];
  const handoffs: ProjectedSession["handoffs"] = [];
  const reworks: ProjectedSession["reworks"] = [];
  let evaluation: AgentEvent | undefined;
  let finished = false;

  const ensure = (agentRunId: string, seed?: Partial<AgentRun>): AgentRun => {
    let run = byId.get(agentRunId);
    if (!run) {
      run = {
        agentRunId,
        sessionId: "session-publish-plan",
        role: seed?.role ?? "Agent",
        agentId: seed?.agentId ?? agentRunId,
        title: seed?.title ?? "",
        status: "queued",
        toolCalls: 0,
        inputArtifacts: [],
        outputArtifacts: [],
        ...seed,
      };
      byId.set(agentRunId, run);
      order.push(agentRunId);
    } else if (seed) {
      Object.assign(run, seed);
    }
    return run;
  };

  for (const e of events) {
    const payload = (e.payload ?? {}) as Record<string, unknown>;
    switch (e.type) {
      case "agent_started": {
        if (!e.agentRunId) break;
        ensure(e.agentRunId, {
          role: String(payload.role ?? "Agent"),
          agentId: String(payload.agent ?? e.agentRunId),
          title: String(payload.title ?? ""),
          nodeId: payload.nodeId ? String(payload.nodeId) : undefined,
          instanceId: payload.instanceId
            ? String(payload.instanceId)
            : e.agentRunId.split(":").slice(1).join(":"),
          status: "running",
          startedAt: new Date(Date.parse("2026-09-11T02:41:00Z") + e.sequence * 1500).toISOString(),
        });
        break;
      }
      case "agent_completed": {
        if (!e.agentRunId) break;
        const run = ensure(e.agentRunId);
        run.status = "completed";
        if (typeof e.durationMs === "number") run.durationMs = e.durationMs;
        if (typeof e.tokens === "number") run.tokens = e.tokens;
        run.currentStep = undefined;
        break;
      }
      case "tool_call": {
        if (e.agentRunId) {
          const run = ensure(e.agentRunId);
          run.toolCalls += 1;
          run.currentStep = e.summary;
        }
        break;
      }
      case "tool_result":
        if (e.agentRunId) ensure(e.agentRunId).currentStep = e.summary;
        break;
      case "artifact": {
        if (e.agentRunId && e.artifactId) {
          const run = ensure(e.agentRunId);
          if (!run.outputArtifacts.includes(e.artifactId))
            run.outputArtifacts.push(e.artifactId);
        }
        break;
      }
      case "message": {
        if (e.sourceAgentRunId && e.targetAgentRunId) {
          ensure(e.targetAgentRunId);
          handoffs.push({
            from: e.sourceAgentRunId,
            to: e.targetAgentRunId,
            summary: e.summary,
            sequence: e.sequence,
          });
        }
        break;
      }
      case "retry": {
        if (e.agentRunId) {
          ensure(e.agentRunId);
          reworks.push({ agentRunId: e.agentRunId, summary: e.summary });
        }
        break;
      }
      case "evaluation":
        evaluation = e;
        break;
      case "output":
        if (payload.final === true) finished = true;
        break;
      default:
        break;
    }
  }
  return {
    agentRuns: order.map((id) => byId.get(id)!),
    agentRunById: byId,
    handoffs,
    reworks,
    evaluation,
    finished,
  };
}

/* ---------- Live Execution Graph (V3 §11.4, §20) ---------- */

export interface ExecutionGraph {
  nodes: ExecutionGraphNode[];
  edges: ExecutionGraphEdge[];
  latestNodeId: string | null;
}

const TOOL_GROUP = (summary = "") =>
  /check|conflict|overlap/i.test(summary) ? "verify" : "tool";

export function projectExecutionGraph(
  events: AgentEvent[],
  options: { groupMode?: "agent-run" | "turn" | "none"; hideTools?: boolean } = {},
): ExecutionGraph {
  const groupMode = options.groupMode ?? "agent-run";
  const hideTools = options.hideTools ?? true;
  const session = projectSession(events);
  const nodes: ExecutionGraphNode[] = [];
  const edges: ExecutionGraphEdge[] = [];
  const seen = new Set<string>();
  const push = (n: ExecutionGraphNode) => {
    if (seen.has(n.id)) return;
    seen.add(n.id);
    nodes.push(n);
  };

  push({
    id: `task:${sessionRunId}`,
    kind: "task",
    status: "completed",
    title: "用户任务",
    summary: "产品发布排期与资源冲突校验",
  });
  let prevTop = `task:${sessionRunId}`;
  const agentNodeId = (agentRunId: string) => `agent:${agentRunId}`;

  for (const run of session.agentRuns) {
    const node = agentNodeId(run.agentRunId);
    push({
      id: node,
      kind: "agent",
      status: run.status,
      title: run.role === "Executor" && run.agentRunId.endsWith("executor-2")
        ? "Executor · 返工"
        : run.role,
      summary: run.currentStep || run.title,
      agentRunId: run.agentRunId,
      durationMs: run.durationMs,
    });
    edges.push({
      id: `seq:${prevTop}->${node}`,
      source: prevTop,
      target: node,
      type: "sequence",
    });
    if (!hideTools && (run.toolCalls > 0 || run.outputArtifacts.length)) {
      for (const e of events) {
        const payload = (e.payload ?? {}) as Record<string, unknown>;
        if (e.agentRunId !== run.agentRunId) continue;
        if (e.type === "tool_call") {
          const tid = `tool:${e.callId}`;
          push({
            id: tid,
            kind: TOOL_GROUP(e.summary) as "tool" | "verify",
            status: "completed",
            title: String(payload.tool ?? "tool"),
            summary: e.summary,
            agentRunId: run.agentRunId,
            eventId: e.eventId,
            callId: e.callId,
          });
          edges.push({ id: `sub:${node}->${tid}`, source: node, target: tid, type: "subcall" });
        } else if (e.type === "artifact") {
          const aid = `artifact:${e.artifactId}`;
          push({
            id: aid,
            kind: "artifact",
            status: "completed",
            title: e.summary ?? "产物",
            agentRunId: run.agentRunId,
            eventId: e.eventId,
            artifactId: e.artifactId,
          });
          edges.push({ id: `sub:${node}->${aid}`, source: node, target: aid, type: "subcall" });
        }
      }
    }
    prevTop = node;
  }

  for (const h of session.handoffs) {
    edges.push({
      id: `handoff:${h.from}->${h.to}:${h.sequence}`,
      source: agentNodeId(h.from),
      target: agentNodeId(h.to),
      type: "handoff",
    });
  }
  for (const r of session.reworks) {
    edges.push({
      id: `feedback:${r.agentRunId}`,
      source: "agent:" + runKey("critic-1"),
      target: agentNodeId(r.agentRunId),
      type: "feedback",
    });
  }

  void groupMode; // turn/none grouping arrives with the full Trace phase
  const last = nodes[nodes.length - 1];
  return { nodes, edges, latestNodeId: last?.id ?? null };
}

/* Events belonging to one AgentRun, in stream order, for the expandable
   child-process view (V3 §9.5). Grouping stays in this layer so Chat and the
   Inspector never re-parse raw events. */
export function groupEventsByRun(
  events: AgentEvent[],
): Map<string, AgentEvent[]> {
  const byRun = new Map<string, AgentEvent[]>();
  for (const e of events) {
    if (!e.agentRunId) continue;
    const list = byRun.get(e.agentRunId);
    if (list) list.push(e);
    else byRun.set(e.agentRunId, [e]);
  }
  return byRun;
}

/* ---------- Chat transcript (V3 §6–§9, §20) ---------- */

export interface ChatStep {
  kind: "thinking" | "tool" | "artifact" | "message" | "retry" | "output";
  label: string;
  summary?: string;
  eventId?: string;
  callId?: string;
  artifactId?: string;
  done: boolean;
  durationMs?: number;
}

export interface ChatAgentRow {
  agentRunId: string;
  role: string;
  title: string;
  status: AgentRun["status"];
  step?: string;
  toolCalls: number;
  tokens?: number | null;
  durationMs?: number;
  steps: ChatStep[];
}

export interface Conversation {
  agents: ChatAgentRow[];
  finalAnswer?: string;
  counts: { agents: number; tools: number; messages: number; artifacts: number };
  running: boolean;
}

export function projectConversation(events: AgentEvent[]): Conversation {
  const session = projectSession(events);
  const byRun = groupEventsByRun(events);
  const agents: ChatAgentRow[] = session.agentRuns.map((run) => {
    const steps: ChatStep[] = [];
    for (const e of byRun.get(run.agentRunId) ?? []) {
      const payload = (e.payload ?? {}) as Record<string, unknown>;
      switch (e.type) {
        case "output":
          if (payload.step === "thinking")
            steps.push({ kind: "thinking", label: "思考", summary: e.summary, eventId: e.eventId, done: true });
          break;
        case "tool_call":
          steps.push({
            kind: "tool",
            label: String(payload.tool ?? "工具调用"),
            summary: e.summary,
            eventId: e.eventId,
            callId: e.callId,
            done: false,
          });
          break;
        case "tool_result": {
          const tool = [...steps].reverse().find((s) => s.kind === "tool" && s.callId === e.callId);
          if (tool) {
            tool.done = true;
            tool.durationMs = e.durationMs;
            tool.summary = e.summary;
          } else {
            steps.push({ kind: "tool", label: "工具结果", summary: e.summary, done: true, eventId: e.eventId });
          }
          break;
        }
        case "artifact":
          steps.push({
            kind: "artifact",
            label: "生成产物",
            summary: e.summary,
            artifactId: e.artifactId,
            eventId: e.eventId,
            done: true,
          });
          break;
        case "retry":
          steps.push({ kind: "retry", label: "有界返工", summary: e.summary, eventId: e.eventId, done: true });
          break;
        default:
          break;
      }
    }
    return {
      agentRunId: run.agentRunId,
      role: run.role,
      title: run.title,
      status: run.status,
      step: run.currentStep,
      toolCalls: run.toolCalls,
      tokens: run.tokens,
      durationMs: run.durationMs,
      steps,
    };
  });
  const handoffs = session.handoffs.length;
  const finalOutput = [...events]
    .reverse()
    .find((e) => e.type === "output" && (e.payload as { final?: boolean })?.final === true);
  const tools = agents.reduce((sum, a) => sum + a.toolCalls, 0);
  const artifacts = new Set(
    session.agentRuns.flatMap((r) => r.outputArtifacts),
  ).size;
  return {
    agents,
    finalAnswer: finalOutput?.summary,
    counts: {
      agents: agents.length,
      tools,
      messages: handoffs,
      artifacts,
    },
    running: !session.finished,
  };
}

/* Topology seed shared by the Team placeholder view. */
export const topology = sessionGraph;
