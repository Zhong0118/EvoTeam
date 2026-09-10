import { z } from "zod";
import { refSchema } from "./schema";

// F0 执行契约；与 Python evoteam/execution/models.py 共用
// ../fixtures/execution-samples.json 中的同一份样例验证两侧一致。

export const executionStatusSchema = z.enum([
  "accepted",
  "running",
  "completed",
  "failed",
  "timed_out",
  "cancelled",
  "interrupted",
]);
export const executionPhaseSchema = z.enum([
  "accepted",
  "executing",
  "evaluating",
  "sealing",
  "terminal",
]);
export const terminalExecutionStatuses = [
  "completed",
  "failed",
  "timed_out",
  "cancelled",
  "interrupted",
] as const;
export const isTerminalStatus = (
  status: z.infer<typeof executionStatusSchema>,
): boolean =>
  (terminalExecutionStatuses as readonly string[]).includes(status);

export const executionViewSchema = z.strictObject({
  execution_id: z.string().min(1),
  run_id: z.string().min(1),
  strategy_id: z.string().min(1),
  status: executionStatusSchema,
  phase: executionPhaseSchema,
  created_at: z.string(),
  started_at: z.string().nullable(),
  finished_at: z.string().nullable(),
  strategy_ref: refSchema.nullable(),
  last_sequence: z.number().int().min(-1),
  sealed_run_id: z.string().nullable(),
  error_code: z.string().nullable(),
  safe_message: z.string().nullable(),
  cancel_requested: z.boolean(),
});

export const traceEventViewSchema = z.strictObject({
  event_id: z.string().min(1),
  event_type: z.string().min(1),
  timestamp: z.string(),
  sequence: z.number().int().min(0),
  run_id: z.string().nullable(),
  node_id: z.string().nullable(),
  instance_id: z.string().nullable(),
  caused_by: z.array(z.string()),
  node_state: z.string().nullable(),
  output: z.unknown().nullable(),
  config: z.record(z.string(), z.unknown()).nullable(),
});

export const executionEventsPageSchema = z.strictObject({
  items: z.array(traceEventViewSchema),
  next_after_sequence: z.number().int().min(-1),
  terminal: z.boolean(),
});

const text = (value: unknown): value is string =>
  typeof value === "string" && value.trim().length > 0;
const intAtLeast = (value: unknown, min: number): value is number =>
  typeof value === "number" && Number.isInteger(value) && value >= min;
const stringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");
const entry = (value: unknown): Record<string, unknown> | null =>
  typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;

// 镜像 domain/planning.py 的 PlanningInput 校验；错误信息携带具体 ID，
// 供 F3 表单定位到字段。两边规则不一致时以同份样例测试暴露。
export function validatePlanningInput(inputs: unknown): string[] {
  const issues: string[] = [];
  const data = entry(inputs);
  if (data === null) return ["任务输入必须是对象"];
  if (!text(data.goal)) issues.push("缺少必需字段 goal");
  if (!intAtLeast(data.deadline_hour, 0))
    issues.push("deadline_hour 必须是非负整数小时");
  if (!intAtLeast(data.budget_minor, 0))
    issues.push("budget_minor 必须是非负整数最小货币单位");
  if (typeof data.currency !== "string" || !/^[A-Z]{3}$/.test(data.currency))
    issues.push("currency 必须是三位大写字母");
  if (!Array.isArray(data.milestones)) issues.push("缺少必需字段 milestones");

  const people = Array.isArray(data.people) ? data.people : [];
  if (people.length === 0) issues.push("people 至少需要一名人员");
  const seenPeople = new Set<string>();
  for (const raw of people) {
    const person = entry(raw);
    if (person === null) {
      issues.push("人员条目必须是对象");
      continue;
    }
    if (!text(person.person_id)) issues.push("人员缺少 person_id");
    else if (seenPeople.has(person.person_id))
      issues.push(`person_id 必须唯一: ${person.person_id}`);
    else seenPeople.add(person.person_id);
    if (!stringArray(person.skills)) issues.push("skills 必须是字符串数组");
    if (!intAtLeast(person.hourly_cost_minor, 0))
      issues.push("hourly_cost_minor 必须是非负整数");
    if (!intAtLeast(person.available_from_hour, 0))
      issues.push("available_from_hour 必须是非负整数");
    if (!intAtLeast(person.available_until_hour, 0))
      issues.push("available_until_hour 必须是非负整数");
    if (
      intAtLeast(person.available_from_hour, 0) &&
      intAtLeast(person.available_until_hour, 0) &&
      person.available_until_hour <= person.available_from_hour
    )
      issues.push(`人员可用区间必须为正: ${person.person_id}`);
  }

  const works = Array.isArray(data.work_items) ? data.work_items : [];
  if (works.length === 0) issues.push("work_items 至少需要一个工作项");
  const seenWorks = new Set<string>();
  const parsedWorks: { work_id: string; dependencies: string[] }[] = [];
  let worksValid = true;
  for (const raw of works) {
    const work = entry(raw);
    if (work === null) {
      issues.push("工作项条目必须是对象");
      worksValid = false;
      continue;
    }
    if (!text(work.work_id)) {
      issues.push("工作项缺少 work_id");
      worksValid = false;
      continue;
    }
    const duplicateWork = seenWorks.has(work.work_id);
    if (duplicateWork) issues.push(`work_id 必须唯一: ${work.work_id}`);
    else seenWorks.add(work.work_id);
    if (!text(work.description)) issues.push(`工作项缺少描述: ${work.work_id}`);
    if (!intAtLeast(work.duration_hours, 1))
      issues.push(`duration_hours 必须是正整数: ${work.work_id}`);
    if (!stringArray(work.required_skills))
      issues.push(`required_skills 必须是字符串数组: ${work.work_id}`);
    if (!stringArray(work.dependencies) || !work.dependencies.every(text)) {
      issues.push(`dependencies 必须是非空字符串数组: ${work.work_id}`);
      worksValid = false;
      continue;
    }
    if (new Set(work.dependencies).size !== work.dependencies.length)
      issues.push(`dependencies 必须唯一: ${work.work_id}`);
    // 重复 work_id 已报告唯一性问题；不进入拓扑检查，避免误报循环。
    if (!duplicateWork)
      parsedWorks.push({ work_id: work.work_id, dependencies: work.dependencies });
  }

  const known = seenWorks;
  const unknownDeps = new Set<string>();
  for (const work of parsedWorks)
    for (const dep of work.dependencies)
      if (!known.has(dep)) unknownDeps.add(dep);
  if (unknownDeps.size > 0)
    issues.push(`依赖引用了未知工作项: ${[...unknownDeps].join(", ")}`);

  if (worksValid && unknownDeps.size === 0) {
    const indegree = new Map<string, number>(
      parsedWorks.map((work) => [work.work_id, 0]),
    );
    const followers = new Map<string, string[]>(
      parsedWorks.map((work) => [work.work_id, []]),
    );
    for (const work of parsedWorks)
      for (const dep of work.dependencies) {
        indegree.set(work.work_id, (indegree.get(work.work_id) ?? 0) + 1);
        followers.get(dep)?.push(work.work_id);
      }
    const queue = parsedWorks
      .filter((work) => (indegree.get(work.work_id) ?? 0) === 0)
      .map((work) => work.work_id);
    let processed = 0;
    while (queue.length > 0) {
      const current = queue.shift();
      if (current === undefined) break;
      processed += 1;
      for (const next of followers.get(current) ?? []) {
        const left = (indegree.get(next) ?? 0) - 1;
        indegree.set(next, left);
        if (left === 0) queue.push(next);
      }
    }
    if (processed < parsedWorks.length) {
      const cyclic = parsedWorks
        .filter((work) => (indegree.get(work.work_id) ?? 0) > 0)
        .map((work) => work.work_id);
      issues.push(`工作项依赖存在循环: ${cyclic.join(", ")}`);
    }
  }

  const milestones = Array.isArray(data.milestones) ? data.milestones : [];
  const seenMilestones = new Set<string>();
  for (const raw of milestones) {
    const milestone = entry(raw);
    if (milestone === null) {
      issues.push("里程碑条目必须是对象");
      continue;
    }
    if (!text(milestone.milestone_id)) issues.push("里程碑缺少 milestone_id");
    else if (seenMilestones.has(milestone.milestone_id))
      issues.push(`milestone_id 必须唯一: ${milestone.milestone_id}`);
    else seenMilestones.add(milestone.milestone_id);
    if (!stringArray(milestone.work_ids) || milestone.work_ids.length === 0)
      issues.push(`里程碑 work_ids 至少一项: ${milestone.milestone_id}`);
    else {
      if (new Set(milestone.work_ids).size !== milestone.work_ids.length)
        issues.push(`里程碑 work_ids 必须唯一: ${milestone.milestone_id}`);
      const unknown = milestone.work_ids.filter((id) => !known.has(id));
      if (unknown.length > 0)
        issues.push(
          `里程碑引用了未知工作项: ${milestone.milestone_id} -> ${unknown.join(", ")}`,
        );
    }
    if (!intAtLeast(milestone.deadline_hour, 0))
      issues.push(`里程碑期限必须是非负整数: ${milestone.milestone_id}`);
  }
  return issues;
}

export const submitExecutionSchema = z
  .strictObject({
    request_id: z.uuid(),
    strategy_id: z.string().min(1),
    task: z.strictObject({
      task_id: z.string().min(1),
      task_type: z.literal("project_planning"),
      instruction: z.string().min(1),
      input_schema: z.strictObject({
        id: z.literal("project-planning-input"),
        version: z.literal("1"),
      }),
      inputs: z.record(z.string(), z.unknown()),
    }),
  })
  .check((ctx) => {
    for (const message of validatePlanningInput(ctx.value.task.inputs)) {
      ctx.issues.push({
        code: "custom",
        input: ctx.value.task.inputs,
        message,
        path: ["task", "inputs"],
      });
    }
  });

export type ExecutionStatus = z.infer<typeof executionStatusSchema>;
export type ExecutionPhase = z.infer<typeof executionPhaseSchema>;
export type ExecutionView = z.infer<typeof executionViewSchema>;
export type TraceEventView = z.infer<typeof traceEventViewSchema>;
export type ExecutionEventsPage = z.infer<typeof executionEventsPageSchema>;
export type SubmitExecution = z.infer<typeof submitExecutionSchema>;
