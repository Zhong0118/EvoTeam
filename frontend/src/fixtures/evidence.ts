import type {
  Run,
  Strategy,
  Evolution,
  Validation,
  TraceEvent,
} from "../data/schema";
const strategyId = "demo-project-planning";
const ref = (version: number) => ({ strategy_id: strategyId, version });
const asset = (id: string, version = "1") => ({ id, version });
const roles = ["planner", "executor", "critic"];
export const current: Strategy = {
  metadata: { ref: ref(0), parent: null, generation: 0, status: "current" },
  definition: {
    agents: roles.map((role) => ({
      node_id: role,
      config_id: `${role}-default`,
      role,
      prompt_ref: asset(role, "v0"),
      model_ref: asset("fixture-model"),
      skill_refs: [],
      tool_policy: { allowed_tools: [], required_tools: [] },
    })),
    edges: [
      { source: "planner", target: "executor", condition_ref: null },
      { source: "executor", target: "critic", condition_ref: null },
    ],
  },
};
export const candidate: Strategy = structuredClone(current);
candidate.metadata = {
  ref: ref(1),
  parent: ref(0),
  generation: 1,
  status: "rejected",
};
candidate.definition.agents[1].prompt_ref = asset(
  "executor",
  "v1-resource-check",
);
const metric = (success: boolean | null, tokens: number | null) => ({
  quality: success === null ? null : success ? 1 : 0,
  success,
  hard_constraint_errors: success === null ? null : success ? 0 : 1,
  tokens,
  cost: null,
  latency_seconds: tokens === null ? null : 18.4,
  agent_count: 3,
  tool_calls: 0,
  retry_count: 0,
});
const titles = [
  "产品发布计划：从需求梳理到交付验收",
  "研发排期：共享工程师的资源冲突",
  "依赖校验：接口联调与前置任务",
  "超时记录：尚未获得完整产物",
];
export const runs: Run[] = titles.map((title, i) => ({
  run_id: `fixture-run-${i + 1}`,
  task_id: `fixture-task-${i + 1}`,
  task_scope: "project_planning",
  strategy: ref(0),
  purpose: i === 2 ? "validation" : "online",
  status: i === 3 ? "timed_out" : "completed",
  sealed_at: `2026-09-09T0${8 - i}:30:00Z`,
  evaluation: {
    metrics: {
      ...metric(i === 3 ? null : i !== 1, i === 3 ? null : 2480 + i * 317),
      agent_count: i === 3 ? null : i === 1 ? 5 : 3,
    },
    evaluator_ref: asset("rules"),
    issues:
      i === 1
        ? [
            {
              code: "resource_overlap",
              message: "工程师 Lin 的两个工作项在第 4–6 小时重叠。",
              severity: "error",
              evidence_refs: ["work:implementation"],
              node_id: "executor",
            },
          ]
        : [],
    missing_metrics: ["cost"],
  },
  task:
    i === 3
      ? null
      : {
          task_id: `fixture-task-${i + 1}`,
          instruction: title,
          inputs: {
            goal: title,
            deadline_hour: 24,
            budget_minor: 200000,
            currency: "CNY",
            people: [
              { person_id: "Lin", skills: ["engineering"] },
              { person_id: "Chen", skills: ["design"] },
            ],
            work_items: [
              {
                work_id: "design",
                description: "需求拆解与方案设计",
                dependencies: [],
              },
              {
                work_id: "implementation",
                description: "功能实现与接口联调",
                dependencies: ["design"],
              },
              {
                work_id: "review",
                description: "交付检查与验收",
                dependencies: ["implementation"],
              },
            ],
          },
        },
  plan:
    i === 3
      ? null
      : {
          schedule: [
            {
              work_id: "design",
              person_id: i === 1 ? "Lin" : "Chen",
              start_hour: 0,
              end_hour: i === 1 ? 6 : 4,
            },
            {
              work_id: "implementation",
              person_id: "Lin",
              start_hour: 4,
              end_hour: 12,
            },
            {
              work_id: "review",
              person_id: "Chen",
              start_hour: 12,
              end_hour: 16,
            },
          ],
          risks: ["共享人员的可用时间需要在交付前再次核对。"],
          adjustments: [],
          validation_notes: ["时间使用从项目开始计算的整数小时。"],
        },
  nodes: i === 3 ? [] : current.definition.agents,
  edges: i === 3 ? [] : current.definition.edges,
  instances:
    i === 3
      ? []
      : [...roles, ...(i === 1 ? ["executor", "critic"] : [])].map(
          (role, n) => ({
            instance_id: `fixture-${i}-${role}-${n}`,
            node_id: role,
            state: "completed",
            messages: [
              {
                message_id: `msg-${i}-${n}`,
                sender_node_id: n ? roles[(n - 1) % 3] : null,
                recipient_node_id: role,
                source_event_ids: [],
              },
            ],
            output:
              role === "executor"
                ? { summary: "按人员、依赖和期限编排工作项" }
                : role === "critic"
                  ? { passed: i !== 1, issues: i === 1 ? ["资源冲突"] : [] }
                  : { summary: "提取工作项、人员与硬约束" },
          }),
        ),
  termination_reason: i === 3 ? "timeout" : null,
}));
export function eventsFor(run: Run): TraceEvent[] {
  return (run.instances ?? []).flatMap((ins, i) =>
    ["agent_started", "agent_completed"].map((type, j) => ({
      event_id: `event-${run.run_id}-${i * 2 + j}`,
      event_type: type,
      timestamp: run.sealed_at,
      sequence: i * 2 + j,
      run_id: run.run_id,
      node_id: ins.node_id,
      instance_id: ins.instance_id,
      caused_by: i * 2 + j ? [`event-${run.run_id}-${i * 2 + j - 1}`] : [],
    })),
  );
}
export const evolutions: Evolution[] = [
  {
    evolution_id: "fixture-evolution-1",
    trigger: {
      trigger_id: "fixture-trigger-1",
      strategy: ref(0),
      trigger_type: "repeated_failure",
      reason: "样例：重复出现人员资源冲突，提出 Prompt 候选进行隔离比较。",
      evidence_run_ids: ["fixture-run-2"],
      policy_ref: asset("fixture-monitor"),
    },
    candidates: [ref(1)],
    gate_results: [
      {
        validation_id: "fixture-validation-1",
        decision: "continue_sampling",
        policy_ref: asset("fixture-gate"),
        reasons: [
          "仅有 2 个独立任务，未满足研究协议的最低样本门槛。",
          "样例用于说明证据不足时的拒绝路径，不构成实际实验结果。",
        ],
        improvement_attribution_ref: "fixture-attribution",
      },
    ],
    promoted: null,
    rollback_target: null,
    termination_reason: "候选未晋级；当前服务版本维持 v0",
  },
  {
    evolution_id: "fixture-evolution-2",
    trigger: {
      trigger_id: "fixture-trigger-2",
      strategy: ref(0),
      trigger_type: "repeated_failure",
      reason: "缺少归因与验证证据的样例",
      evidence_run_ids: [],
      policy_ref: asset("fixture-monitor"),
    },
    candidates: [],
    gate_results: [],
    promoted: null,
    rollback_target: null,
    termination_reason: null,
  },
];
export const validation: Validation = {
  validation_id: "fixture-validation-1",
  current: ref(0),
  candidate: ref(1),
  plan: {
    dataset_ref: asset("fixture-validation"),
    evaluator_ref: asset("rules"),
    repeats: 1,
  },
  current_metrics: metric(false, 2700),
  candidate_metrics: metric(true, 3200),
  current_summary: {
    success_count: 1,
    total_count: 2,
    independent_task_count: 2,
  },
  candidate_summary: {
    success_count: 2,
    total_count: 2,
    independent_task_count: 2,
  },
  limitations: ["开发样例；不可用于宣称收益", "独立样本不足，随机种子未应用"],
  pairs: [],
};
export function fixtureData(path: string): unknown {
  const u = new URL(path, "http://fixture");
  const parts = u.pathname.split("/").filter(Boolean);
  if (parts[0] === "runs" && parts.length === 1) {
    const items =
      u.searchParams.get("strategy_id") === strategyId
        ? runs.filter(
            (r) =>
              !u.searchParams.get("purpose") ||
              r.purpose === u.searchParams.get("purpose"),
          )
        : [];
    return { items, next_cursor: null };
  }
  if (parts[0] === "runs") {
    const r = runs.find((r) => r.run_id === parts[1]);
    if (!r) throw new Error("404：该样例记录不存在");
    return parts[2] === "events" ? { items: eventsFor(r) } : r;
  }
  if (parts[0] === "strategies") {
    if (parts[1] !== strategyId) throw new Error("404：策略不存在");
    return { items: [current, candidate], current: ref(0) };
  }
  if (parts[0] === "evolutions" && parts.length === 1)
    return {
      items: u.searchParams.get("strategy_id") === strategyId ? evolutions : [],
      next_cursor: null,
    };
  const record = evolutions.find((r) => r.evolution_id === parts[1]);
  if (!record) throw new Error("404：演进记录不存在");
  return {
    record,
    attributions: record.candidates.length
      ? [
          {
            report_id: "fixture-attribution",
            task_scope: "project_planning",
            needs_more_evidence: true,
            claims: [
              {
                kind: "origin",
                target: "executor",
                explanation:
                  "样例归因：排期阶段产生资源重叠，仍需反事实证据核对。",
                confidence: 0.7,
                evidence_refs: ["fixture-run-2"],
              },
              {
                kind: "control",
                target: "critic",
                explanation: "样例归因：审查阶段没有阻止冲突产物进入最终结果。",
                confidence: 0.6,
                evidence_refs: ["fixture-run-2"],
              },
            ],
          },
        ]
      : [],
    proposals: record.candidates.length
      ? [
          {
            proposal_id: "fixture-proposal",
            operation: "update_prompt",
            target: "executor",
            rationale: "加入明确的资源占用检查步骤",
            attribution_ref: "fixture-attribution",
          },
        ]
      : [],
    validations: record.candidates.length ? [validation] : [],
    strategies: record.candidates.length ? [current, candidate] : [current],
  };
}
