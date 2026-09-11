import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ChatView } from "./chat-view";
import { buildAgentSpans } from "./session-data";
import type { Run, TraceEvent } from "../../data/schema";

const detail = {
  run_id: "run-1",
  task_id: "task-1",
  strategy: { strategy_id: "s", version: 3 },
  purpose: "online",
  status: "completed",
  sealed_at: "2026-09-11T08:31:12Z",
  evaluation: {
    metrics: {
      quality: 1,
      success: true,
      hard_constraint_errors: 0,
      tokens: 1200,
      cost: null,
      latency_seconds: 18,
      agent_count: 3,
      tool_calls: 0,
      retry_count: 0,
    },
    evaluator_ref: { id: "e", version: "1" },
    issues: [],
    missing_metrics: [],
  },
  task: { task_id: "task-1", instruction: "为网站上线生成排期", inputs: null },
  plan: {
    schedule: [
      { work_id: "w1", person_id: "alice", start_hour: 0, end_hour: 4 },
    ],
    milestones: [{ milestone_id: "m1", completion_hour: 4 }],
    risks: [],
    adjustments: [],
    validation_notes: ["单位为整数小时"],
  },
  nodes: [],
  edges: [],
  instances: [
    {
      instance_id: "planner-1",
      node_id: "planner",
      state: "completed",
      input_tokens: 800,
      output_tokens: 400,
      messages: [],
      output: { summary: "拆解任务与约束" },
    },
  ],
  termination_reason: null,
} as unknown as Run;

const events: TraceEvent[] = [
  {
    event_id: "e0",
    event_type: "task_created",
    timestamp: "2026-09-11T08:30:00Z",
    sequence: 0,
    run_id: "run-1",
    node_id: null,
    instance_id: null,
    caused_by: [],
  },
  {
    event_id: "e1",
    event_type: "agent_completed",
    timestamp: "2026-09-11T08:30:20Z",
    sequence: 1,
    run_id: "run-1",
    node_id: "planner",
    instance_id: "planner-1",
    caused_by: ["e0"],
    node_state: "completed",
    output: { summary: "拆解任务与约束" },
    config: null,
  },
];

describe("ChatView", () => {
  it("renders the coding-agent transcript with a foldable process block", () => {
    const spans = buildAgentSpans(detail, events);
    render(
      <ChatView
        detail={detail}
        spans={spans}
        replayToken={0}
        notify={vi.fn()}
        onOpenArtifact={vi.fn()}
        onOpenEvents={vi.fn()}
      />,
    );
    expect(screen.getByText("为网站上线生成排期")).toBeVisible();
    expect(screen.getAllByText(/已完成/).length).toBeGreaterThan(0);
    expect(screen.getByText(/1 个 Agent · 0 次协作消息 · 1 个产物/)).toBeVisible();
    fireEvent.click(screen.getByText(/1 个 Agent · 0 次协作消息/));
    expect(screen.getByText("planner")).toBeVisible();
    expect(screen.getByText("拆解任务与约束")).toBeVisible();
    expect(screen.getByText("1.2k")).toBeVisible();
  });

  it("links the real sealed evidence export", () => {
    const spans = buildAgentSpans(detail, events);
    render(
      <ChatView
        detail={detail}
        spans={spans}
        replayToken={0}
        notify={vi.fn()}
        onOpenArtifact={vi.fn()}
        onOpenEvents={vi.fn()}
      />,
    );
    expect(
      screen
        .getByText("证据导出")
        .closest("a")
        ?.getAttribute("href"),
    ).toBe("/v1/runs/run-1/export");
  });
});
