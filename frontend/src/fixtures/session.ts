/* Session workspace fixtures — development samples only (V3 §33 Phase 7).
   The shapes here follow the V3 §19/§20 target contracts so that the same
   projections serve fixture and real data later. Never present these numbers
   as measured model results. */

export interface SessionSummary {
  sessionId: string;
  title: string;
  sub: string;
  status: "running" | "completed" | "queued";
  strategyVersion: number;
  updatedAt: string;
}

export const defaultSessionId = "session-publish-plan";

export const sessions: SessionSummary[] = [
  {
    sessionId: defaultSessionId,
    title: "产品发布排期：识别共享工程师的资源冲突",
    sub: "项目计划 · Planner → Executor → Verifier → Critic",
    status: "running",
    strategyVersion: 7,
    updatedAt: "2026-09-11T02:41:00Z",
  },
  {
    sessionId: "session-dependency-check",
    title: "接口联调依赖校验与里程碑重排",
    sub: "项目计划 · 2 个产物",
    status: "completed",
    strategyVersion: 7,
    updatedAt: "2026-09-10T12:05:00Z",
  },
  {
    sessionId: "session-budget-review",
    title: "预算约束下的交付范围收窄分析",
    sub: "项目计划 · 一次有界返工",
    status: "completed",
    strategyVersion: 6,
    updatedAt: "2026-09-09T09:20:00Z",
  },
];

export function sessionById(id: string): SessionSummary {
  return (
    sessions.find((s) => s.sessionId === id) ?? {
      sessionId: id,
      title: "新会话",
      sub: "尚未开始执行",
      status: "queued",
      strategyVersion: 7,
      updatedAt: new Date().toISOString(),
    }
  );
}
