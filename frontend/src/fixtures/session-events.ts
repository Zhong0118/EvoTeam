/* Scripted session event stream for the workspace fixture. Event vocabulary
   mirrors the persisted TraceEvent names used by the current read-only API
   (task_created / team_created / agent_started / agent_message / tool_called /
   tool_result / agent_completed / evaluation_completed / run_sealed). The
   shape is an envelope per run so projections can derive AgentRun identity
   from run_id + instance_id exactly as V3 §19 prescribes. Development
   sample data — never present as measured model results. */
import type { AgentEvent } from "../features/runtime/types";

export interface SessionGraphSeed {
  nodes: { node_id: string; role: string; title: string }[];
  edges: { source: string; target: string; condition: boolean }[];
}

export const sessionRunId = "fixture-run-live-1";
export const sessionGraph: SessionGraphSeed = {
  nodes: [
    { node_id: "planner", role: "Planner", title: "任务拆解与约束识别" },
    { node_id: "executor", role: "Executor", title: "生成发布排期" },
    { node_id: "verifier", role: "Verifier", title: "资源冲突检查" },
    { node_id: "critic", role: "Critic", title: "计划审查" },
  ],
  edges: [
    { source: "planner", target: "executor", condition: false },
    { source: "executor", target: "verifier", condition: false },
    { source: "verifier", target: "critic", condition: false },
  ],
};

let seq = 0;
const event = (
  type: AgentEvent["type"],
  extra: Partial<AgentEvent> & Pick<AgentEvent, "payload">,
): AgentEvent => ({
  eventId: `fx-event-${++seq}`,
  sessionId: "session-publish-plan",
  sequence: seq,
  type,
  ...extra,
});

const run = (id: string) => `${sessionRunId}:${id}`;

export const sessionEventStream: AgentEvent[] = [
  event("agent_started", {
    agentRunId: run("planner-1"),
    payload: {
      role: "Planner",
      agent: "planner",
      title: "拆解任务并提取约束引用",
      instanceId: "planner-1",
      nodeId: "planner",
    },
  }),
  event("output", {
    agentRunId: run("planner-1"),
    summary: "识别 3 名共享人员与 4 个依赖边",
    payload: { step: "thinking" },
  }),
  event("artifact", {
    agentRunId: run("planner-1"),
    artifactId: "constraint-set",
    summary: "约束清单 constraints-v1",
    payload: { kind: "structured" },
  }),
  event("agent_completed", {
    agentRunId: run("planner-1"),
    durationMs: 7200,
    tokens: 2140,
    payload: { instanceId: "planner-1" },
  }),
  event("message", {
    sourceAgentRunId: run("planner-1"),
    targetAgentRunId: run("executor-1"),
    summary: "任务拆解 → Executor",
    payload: {},
  }),
  event("agent_started", {
    agentRunId: run("executor-1"),
    payload: {
      role: "Executor",
      agent: "executor",
      title: "生成里程碑与排期",
      instanceId: "executor-1",
      nodeId: "executor",
    },
  }),
  event("tool_call", {
    agentRunId: run("executor-1"),
    callId: "call-schedule-1",
    summary: "排期求解 schedule.solve",
    payload: { tool: "schedule.solve" },
  }),
  event("tool_result", {
    agentRunId: run("executor-1"),
    callId: "call-schedule-1",
    durationMs: 1300,
    summary: "生成 12 个工作项安排",
    payload: { ok: true },
  }),
  event("artifact", {
    agentRunId: run("executor-1"),
    artifactId: "project-plan-v1",
    summary: "发布计划 project-plan.json",
    payload: { kind: "plan" },
  }),
  event("agent_completed", {
    agentRunId: run("executor-1"),
    durationMs: 9800,
    tokens: 3310,
    payload: { instanceId: "executor-1" },
  }),
  event("message", {
    sourceAgentRunId: run("executor-1"),
    targetAgentRunId: run("verifier-1"),
    summary: "计划产物 → Verifier",
    payload: {},
  }),
  event("agent_started", {
    agentRunId: run("verifier-1"),
    payload: {
      role: "Verifier",
      agent: "verifier",
      title: "硬约束检查",
      instanceId: "verifier-1",
      nodeId: "verifier",
    },
  }),
  event("tool_call", {
    agentRunId: run("verifier-1"),
    callId: "call-check-1",
    summary: "check 资源冲突",
    payload: { tool: "constraint_checker.check" },
  }),
  event("tool_result", {
    agentRunId: run("verifier-1"),
    callId: "call-check-1",
    durationMs: 800,
    summary: "发现 1 处人员时段重叠（Lin 第 4–6 小时）",
    payload: { ok: false, code: "resource_overlap" },
  }),
  event("agent_completed", {
    agentRunId: run("verifier-1"),
    durationMs: 3400,
    tokens: 940,
    payload: { instanceId: "verifier-1" },
  }),
  event("message", {
    sourceAgentRunId: run("verifier-1"),
    targetAgentRunId: run("critic-1"),
    summary: "检查结果 → Critic",
    payload: {},
  }),
  event("agent_started", {
    agentRunId: run("critic-1"),
    payload: {
      role: "Critic",
      agent: "critic",
      title: "审查排期与风险",
      instanceId: "critic-1",
      nodeId: "critic",
    },
  }),
  event("retry", {
    agentRunId: run("executor-2"),
    summary: "Critic 返工：修复 Lin 的时段重叠",
    payload: { feedback: true, targetInstance: "executor-2" },
  }),
  event("agent_started", {
    agentRunId: run("executor-2"),
    payload: {
      role: "Executor",
      agent: "executor",
      title: "返工调整排期（有界返工 1/1）",
      instanceId: "executor-2",
      nodeId: "executor",
    },
  }),
  event("artifact", {
    agentRunId: run("executor-2"),
    artifactId: "project-plan-v2",
    summary: "修订后的发布计划 project-plan.json",
    payload: { kind: "plan", revision: 2 },
  }),
  event("agent_completed", {
    agentRunId: run("executor-2"),
    durationMs: 5100,
    tokens: 1880,
    payload: { instanceId: "executor-2" },
  }),
  event("output", {
    agentRunId: run("critic-1"),
    summary: "确认冲突已消除，给出调整说明",
    payload: { step: "thinking" },
  }),
  event("agent_completed", {
    agentRunId: run("critic-1"),
    durationMs: 4200,
    tokens: 1210,
    payload: { instanceId: "critic-1" },
  }),
  event("evaluation", {
    summary: "评价完成：硬约束 0 错误，质量 0.92",
    payload: { success: true, tokens: 9480, latency_seconds: 31.2 },
  }),
  event("output", {
    summary: "最终计划与风险清单已生成",
    payload: { final: true },
  }),
];

/* The scripted user turn shown in the transcript for fixture sessions that
   already produced events before the workspace was opened. */
export const scriptedUserTask =
  "为下季度产品发布生成排期，识别并消除共享工程师的资源冲突，输出里程碑、风险清单与调整说明。";
