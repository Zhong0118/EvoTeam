import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { buildAgentRuns, buildConversation } from "../runtime/projection";
import { ConversationView } from "./conversation-view";
import type { Run, TraceEvent } from "../../data/schema";

const detail = {
  run_id: "run-1",
  task_id: "task-1",
  task_scope: "project_planning",
  strategy: { strategy_id: "s", version: 0 },
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
  task: {
    task_id: "task-1",
    instruction: "为网站上线生成排期",
    inputs: null,
  },
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
      messages: [
        {
          message_id: "m1",
          sender_node_id: null,
          recipient_node_id: "planner",
          source_event_ids: [],
        },
      ],
      output: { summary: "已完成任务拆解" },
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
    event_type: "agent_started",
    timestamp: "2026-09-11T08:30:01Z",
    sequence: 1,
    run_id: "run-1",
    node_id: "planner",
    instance_id: "planner-1",
    caused_by: ["e0"],
    node_state: "running",
    output: null,
    config: null,
  },
  {
    event_id: "e2",
    event_type: "agent_completed",
    timestamp: "2026-09-11T08:30:20Z",
    sequence: 2,
    run_id: "run-1",
    node_id: "planner",
    instance_id: "planner-1",
    caused_by: ["e1"],
    node_state: "completed",
    output: { summary: "已完成任务拆解" },
    config: null,
  },
];

describe("session projection", () => {
  it("projects instances into agent runs keyed by run+instance", () => {
    const agents = buildAgentRuns(detail, events);
    expect(agents).toHaveLength(1);
    expect(agents[0]).toMatchObject({
      agentRunId: "run-1:planner-1",
      nodeId: "planner",
      status: "completed",
      step: "已交付结果",
      startedAt: "2026-09-11T08:30:01Z",
    });
    expect(agents[0].messages[0]).toMatchObject({ to: "planner" });
  });

  it("builds conversation counts without inventing usage", () => {
    const conversation = buildConversation(detail, events);
    expect(conversation).toMatchObject({
      instruction: "为网站上线生成排期",
      counts: { agents: 1, messages: 1, artifacts: 1 },
    });
    expect(conversation.plan?.milestones).toHaveLength(1);
  });
});

describe("ConversationView", () => {
  it("folds the process by default and expands agent rows on demand", () => {
    const conversation = buildConversation(detail, events);
    render(<ConversationView conversation={conversation} onOpenArtifact={vi.fn()} />);
    expect(screen.getByText("为网站上线生成排期")).toBeVisible();
    expect(
      screen.getByText(/1 个 Agent · 1 条协作消息 · 1 个产物/),
    ).toBeVisible();
    expect(screen.queryByText(/已完成任务拆解/)).toBeNull();
    fireEvent.click(screen.getByText(/1 个 Agent · 1 条协作消息/));
    expect(screen.getByText("planner")).toBeVisible();
    expect(screen.getByText("已完成任务拆解")).toBeVisible();
  });

  it("opens the artifact panel from the artifact card", () => {
    const conversation = buildConversation(detail, events);
    const onOpenArtifact = vi.fn();
    render(
      <ConversationView
        conversation={conversation}
        onOpenArtifact={onOpenArtifact}
      />,
    );
    fireEvent.click(screen.getByText("在产物面板打开"));
    expect(onOpenArtifact).toHaveBeenCalledOnce();
  });
});
