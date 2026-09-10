import { describe, expect, it } from "vitest";
import samples from "../fixtures/execution-samples.json";
import {
  executionEventsPageSchema,
  executionViewSchema,
  submitExecutionSchema,
  validatePlanningInput,
} from "./executions";

type Sample = Record<string, Record<string, unknown>>;
const views = samples.views as Sample;
const submits = samples.submit as Sample;
const events = samples.events as Sample;

describe("execution contract samples follow the fixed F0 DTOs", () => {
  it("parses every view sample and keeps status independent of evaluation", () => {
    for (const sample of Object.values(views)) {
      const view = executionViewSchema.parse(sample);
      expect(view.execution_id).toBeTruthy();
    }
    const view = executionViewSchema.parse(views.evaluation_failed);
    expect(view.status).toBe("completed");
    expect("evaluation" in view).toBe(false);
  });

  it("rejects unknown status, phase values and extra fields", () => {
    expect(
      executionViewSchema.safeParse({
        ...views.running,
        status: "in_progress",
      }).success,
    ).toBe(false);
    expect(
      executionViewSchema.safeParse({
        ...views.running,
        phase: "queued",
      }).success,
    ).toBe(false);
    expect(
      executionViewSchema.safeParse({
        ...views.accepted,
        evaluation: null,
      }).success,
    ).toBe(false);
  });

  it("accepts the valid submit sample and rejects broken inputs", () => {
    expect(submitExecutionSchema.parse(submits.valid)).toBeTruthy();
    for (const key of [
      "unknown_dependency",
      "dependency_cycle",
      "missing_milestones_field",
      "duplicate_person",
      "bad_request_id",
    ]) {
      expect(submitExecutionSchema.safeParse(submits[key]).success).toBe(false);
    }
  });

  it("locates planning input violations for the task form", () => {
    const valid = submits.valid as { task: { inputs: Record<string, unknown> } };
    expect(validatePlanningInput(valid.task.inputs)).toEqual([]);
    const broken = submits.unknown_dependency as {
      task: { inputs: Record<string, unknown> };
    };
    const errors = validatePlanningInput(broken.task.inputs);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors.join("\n")).toContain("w9");
  });

  it("reports duplicate work ids without a spurious cycle message", () => {
    const valid = submits.valid as { task: { inputs: Record<string, unknown> } };
    const inputs = structuredClone(valid.task.inputs);
    const workItems = inputs.work_items as Record<string, unknown>[];
    workItems.push(structuredClone(workItems[0]));
    const errors = validatePlanningInput(inputs);
    expect(errors.some((message) => message.includes("必须唯一"))).toBe(true);
    expect(errors.some((message) => message.includes("循环"))).toBe(false);
  });

  it("parses event pages with ordered sequences and a real cursor", () => {
    for (const page of Object.values(events)) {
      const parsed = executionEventsPageSchema.parse(page);
      const sequences = parsed.items.map((event) => event.sequence);
      expect([...sequences].sort((a, b) => a - b)).toEqual(sequences);
    }
    const empty = executionEventsPageSchema.parse(events.empty_page);
    expect(empty.items).toEqual([]);
    expect(empty.next_after_sequence).toBe(-1);
    expect(empty.terminal).toBe(false);
    expect(
      executionEventsPageSchema.safeParse({
        ...events.empty_page,
        extra: true,
      }).success,
    ).toBe(false);
  });
});
