/* Runtime projection contracts — EVOTEAM_FRONTEND_IMPLEMENTATION_SPEC_V3 §19/§20.
   These are frontend view models derived from the existing read-only API
   shape (run/nodes/edges/instances/events). The backend does not emit these
   objects yet; agentRunId is derived as `${run_id}:${instance_id}` (§19). */

export type AgentRunStatus = "queued" | "running" | "completed" | "failed";

export interface AgentRun {
  agentRunId: string;
  sessionId: string;
  parentAgentRunId?: string;
  delegationId?: string;
  nodeId?: string;
  instanceId?: string;
  role: string;
  agentId: string;
  title: string;
  status: AgentRunStatus;
  currentStep?: string;
  startedAt?: string;
  endedAt?: string;
  durationMs?: number;
  toolCalls: number;
  tokens?: number | null;
  inputArtifacts: string[];
  outputArtifacts: string[];
}

export type AgentEventType =
  | "reasoning"
  | "agent_started"
  | "agent_completed"
  | "tool_call"
  | "tool_result"
  | "message"
  | "artifact"
  | "retry"
  | "evaluation"
  | "evolution"
  | "output";

export interface AgentEvent {
  eventId: string;
  sessionId: string;
  agentRunId?: string;
  sequence: number;
  type: AgentEventType;
  summary?: string;
  sourceAgentRunId?: string;
  targetAgentRunId?: string;
  callId?: string;
  artifactId?: string;
  durationMs?: number;
  tokens?: number;
  causedBy?: string[];
  payload: unknown;
}

export type ExecutionNodeKind =
  | "task"
  | "agent"
  | "thinking"
  | "tool"
  | "message"
  | "artifact"
  | "verify"
  | "error"
  | "evolution";

export interface ExecutionGraphNode {
  id: string;
  kind: ExecutionNodeKind;
  status: string;
  title: string;
  summary?: string;
  agentRunId?: string;
  eventId?: string;
  callId?: string;
  artifactId?: string;
  durationMs?: number;
  turn?: number;
  parentId?: string;
}

export interface ExecutionGraphEdge {
  id: string;
  source: string;
  target: string;
  type: "sequence" | "delegation" | "handoff" | "feedback" | "subcall";
}

/* Stable identity keys used by the Chat <-> Graph locate registry (§11.7). */
export type FlowKey =
  | `event:${string}`
  | `agent-run:${string}`
  | `tool:${string}`
  | `message:${string}`
  | `artifact:${string}`;

export const flowKey = {
  event: (id: string): FlowKey => `event:${id}`,
  agentRun: (id: string): FlowKey => `agent-run:${id}`,
  tool: (id: string): FlowKey => `tool:${id}`,
  message: (id: string): FlowKey => `message:${id}`,
  artifact: (id: string): FlowKey => `artifact:${id}`,
} as const;
