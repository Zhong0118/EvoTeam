import { describe, expect, it } from "vitest";
import {
  projectConversation,
  projectExecutionGraph,
  projectSession,
} from "./projections";
import { sessionEventStream, sessionRunId } from "../../fixtures/session-events";

describe("projectSession", () => {
  const full = projectSession(sessionEventStream);

  it("derives AgentRun identity from run_id + instance_id (V3 §19)", () => {
    for (const run of full.agentRuns) {
      expect(run.agentRunId.startsWith(`${sessionRunId}:`)).toBe(true);
      expect(run.instanceId).toBeTruthy();
    }
  });

  it("counts tools and artifacts per run and marks all runs completed", () => {
    expect(full.agentRuns.every((r) => r.status === "completed")).toBe(true);
    const executor = full.agentRuns.find((r) => r.instanceId === "executor-1");
    expect(executor?.toolCalls).toBe(1);
    expect(executor?.outputArtifacts).toContain("project-plan-v1");
  });

  it("records handoffs and the single bounded rework", () => {
    expect(full.handoffs.length).toBeGreaterThanOrEqual(3);
    expect(full.reworks.map((r) => r.agentRunId)).toEqual([
      `${sessionRunId}:executor-2`,
    ]);
    expect(full.finished).toBe(true);
  });

  it("prefix of the stream keeps unfinished runs running", () => {
    const partial = projectSession(sessionEventStream.slice(0, 6));
    const statuses = partial.agentRuns.map((r) => r.status);
    expect(statuses).toContain("running");
    expect(partial.finished).toBe(false);
  });
});

describe("projectConversation", () => {
  it("follows fold priority: final answer appears only after completion", () => {
    const done = projectConversation(sessionEventStream);
    expect(done.finalAnswer).toBeTruthy();
    expect(done.running).toBe(false);
    const mid = projectConversation(sessionEventStream.slice(0, 10));
    expect(mid.finalAnswer).toBeFalsy();
    expect(mid.running).toBe(true);
  });

  it("projects the child-process steps of one AgentRun", () => {
    const done = projectConversation(sessionEventStream);
    const verifier = done.agents.find((a) => a.role === "Verifier");
    expect(verifier?.steps.map((s) => s.kind)).toEqual(["tool"]);
    expect(verifier?.steps[0].done).toBe(true);
  });
});

describe("projectExecutionGraph", () => {
  const graph = projectExecutionGraph(sessionEventStream, { hideTools: true });

  it("starts from the task node and chains agent-run nodes", () => {
    expect(graph.nodes[0].kind).toBe("task");
    const agents = graph.nodes.filter((n) => n.kind === "agent");
    expect(agents.map((a) => a.agentRunId)).toEqual(
      agents.map((a) => a.agentRunId).filter(Boolean),
    );
    expect(new Set(agents.map((a) => a.id)).size).toBe(agents.length);
  });

  it("compact mode hides tool nodes; expanding shows them under their run", () => {
    expect(graph.nodes.some((n) => n.kind === "tool")).toBe(false);
    const open = projectExecutionGraph(sessionEventStream, {
      hideTools: false,
    });
    const tools = open.nodes.filter((n) => n.kind === "tool" || n.kind === "verify");
    expect(tools.length).toBe(2);
    for (const t of tools) expect(t.agentRunId).toBeTruthy();
  });

  it("marks the critic -> executor rework as a feedback edge", () => {
    const feedback = graph.edges.filter((e) => e.type === "feedback");
    expect(feedback.length).toBe(1);
    expect(feedback[0].target).toContain("executor-2");
  });

  it("latestNodeId moves as events arrive", () => {
    const mid = projectExecutionGraph(sessionEventStream.slice(0, 5), {
      hideTools: true,
    });
    expect(mid.latestNodeId).not.toBe(graph.latestNodeId);
  });
});
