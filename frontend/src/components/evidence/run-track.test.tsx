import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { RunTrack, summarizeOutput } from "./run-track";
import type { TraceEvent } from "../../data/schema";

const base = {
  timestamp: "2026-09-11T08:00:00Z",
  run_id: "run-1",
  node_id: null,
  instance_id: null,
  caused_by: [],
  node_state: null,
  output: null,
  config: null,
};
const events: TraceEvent[] = [
  {
    ...base,
    event_id: "e0",
    event_type: "team_created",
    sequence: 0,
    config: { enabled_nodes: ["planner", "executor", "critic"] },
  },
  {
    ...base,
    event_id: "e1",
    event_type: "agent_started",
    sequence: 1,
    node_id: "planner",
    instance_id: "planner-1",
    node_state: "running",
  },
  {
    ...base,
    event_id: "e2",
    event_type: "agent_completed",
    sequence: 2,
    node_id: "planner",
    instance_id: "planner-1",
    node_state: "completed",
    caused_by: ["e1"],
    output: { summary: "提取工作项、人员与硬约束" },
  },
  {
    ...base,
    event_id: "e3",
    event_type: "agent_completed",
    sequence: 3,
    node_id: "critic",
    instance_id: "critic-1",
    node_state: "completed",
    output: { passed: false, issues: ["资源冲突"] },
  },
  { ...base, event_id: "e4", event_type: "run_sealed", sequence: 4 },
];

describe("RunTrack", () => {
  it("renders every step with readable summaries and node badges", () => {
    render(
      <RunTrack events={events} activeIndex={2} streaming={false} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("组装团队")).toBeVisible();
    expect(screen.getAllByText("PLANNER").length).toBe(2);
    expect(screen.getByText("提取工作项、人员与硬约束")).toBeVisible();
    expect(screen.getByText("审查未通过 · 1 个问题")).toBeVisible();
    expect(screen.getByText("证据封存")).toBeVisible();
    expect(screen.getByText("承接 e1…")).toBeVisible();
  });

  it("streams only executed steps while playing", () => {
    render(
      <RunTrack events={events} activeIndex={1} streaming={true} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("开始执行")).toBeVisible();
    expect(screen.queryByText("证据封存")).toBeNull();
    expect(screen.getByText("执行中…")).toBeVisible();
  });

  it("selects a step and exposes structured output", () => {
    const onSelect = vi.fn();
    render(
      <RunTrack events={events} activeIndex={0} streaming={false} onSelect={onSelect} />,
    );
    fireEvent.click(screen.getAllByText("交付结果")[0]);
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ event_id: "e2" }),
    );
    fireEvent.click(screen.getAllByText("展开结构化输出")[0]);
    expect(screen.getAllByText(/提取工作项/).length).toBeGreaterThan(0);
  });
});

describe("summarizeOutput", () => {
  it("describes plan, review and evaluation outputs without judging", () => {
    expect(summarizeOutput({ schedule: [1, 2], risks: [], milestones: [1] })).toBe(
      "排期 2 项工作 · 覆盖 1 个里程碑 · 风险 0 条",
    );
    expect(summarizeOutput({ passed: true, issues: [] })).toBe(
      "审查通过，未发现问题",
    );
    expect(summarizeOutput({ success: false, hard_constraint_errors: 2 })).toBe(
      "规则检查未通过 · 2 个硬约束错误",
    );
    expect(summarizeOutput({ unexpected: true })).toBeNull();
    expect(summarizeOutput(null)).toBeNull();
  });
});
