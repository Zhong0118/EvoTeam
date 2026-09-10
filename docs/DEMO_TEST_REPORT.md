# EvoTeam 初代 Demo 测试记录与下一步建议

> 本文保留组员在 2026-09-09 提交的历史测试与外部调用记录，各节描述对应当时版本。当前实现与审查结果见 [VERSION_COMPARISON](VERSION_COMPARISON.md) 和 [DEVELOPMENT](../DEVELOPMENT.md)；本次审查未重跑这些外部模型实验。

## 1. 文档信息

- 测试日期：2026-09-09
- 项目目录：`/Users/dlg/vscodeProjects/evoteam`
- 模型：`deepseek-v4-flash`
- 模型接口：DeepSeek OpenAI-compatible API
- 当前 Strategy：`project-planning@0`
- 当前执行链：`Planner -> Executor -> Critic -> Deterministic Evaluator`
- 安全说明：本文不记录 API Key；`.env` 已被 `.gitignore` 排除。

## 2. 当前 Demo 的实际能力

当前版本已经实现一个固定的三 Agent 项目规划流水线：

```text
Task
  -> Planner：分析目标和约束
  -> Executor：生成结构化项目排期
  -> Critic：审查 Executor 产物
  -> ConstraintChecker：使用程序规则校验硬约束
  -> SQLite：封存 Run、结果、评价和 Trace
```

当前三个 Agent 使用同一个 DeepSeek 模型，但使用不同 Prompt 和输出 Schema：

| Agent | 输入 | 输出 | 当前权限 |
|---|---|---|---|
| Planner | 原始 Task | `PlanningAnalysis` | 无 Skill、无 Tool |
| Executor | 原始 Task + Planner 输出 | `ProjectPlan` | 无 Skill、无 Tool |
| Critic | 原始 Task + Executor 输出 | `PlanningReview` | 无 Skill、无 Tool |

当前通信由 Orchestrator 集中转发，Agent 之间不直接通信。消息使用 `AgentMessage` 结构化信封，并通过 `source_event_ids` 记录上游事件来源。

## 3. 已完成的测试

### 3.1 本地自动化测试

执行结果：

```text
78 passed, 1 skipped
```

跳过的是需要显式授权和有效 API Key 的真实模型测试。普通测试默认不会连接 DeepSeek，也不会产生费用。

代码规范检查：

```text
All checks passed!
```

本地测试覆盖了：

- FastAPI 路由创建与响应；
- Planner、Executor、Critic 固定编排；
- AgentMessage 和输出 Schema 校验；
- Token 预算、超时和零重试约束；
- SQLite 事件写入、Run 快照和不可覆盖封存；
- 项目排期硬约束校验；
- 重复失败证据与监控状态；
- openJiuwen Adapter 对本地 OpenAI-compatible HTTP 服务的请求格式。

### 3.2 DeepSeek 最小连通性测试

首先查询 `/models`，确认 API Key 有效，并确认账号可用模型包括：

```text
deepseek-v4-flash
deepseek-v4-pro
deepseek-v4-flash-vision-exp
```

随后发送一次最小生成请求：

- 输入：`Reply only: OK`
- 思考模式：关闭
- 最大输出：8 tokens
- 返回：`OK`
- 输入 tokens：8
- 输出 tokens：1
- 总 tokens：9

该测试只证明鉴权、模型 ID 和 Chat Completions 接口可用，不代表完整多 Agent 流程已经通过。

### 3.3 简单三 Agent 项目规划测试

测试任务：

- 1 名人员 Alice；
- `design` 和 `build` 两个工作项；
- `build` 依赖 `design`；
- 总工时 6 小时；
- 截止时间为第 8 小时；
- 人工成本 600，预算 800。

第一次尝试失败在 Planner 阶段：DeepSeek V4 Flash 默认启用思考模式，1,200 个输出 tokens 全部成为 reasoning tokens，最终 JSON 正文为空，返回 `finish_reason=length`。

第一次失败用量：

| Agent | 输入 tokens | 输出/推理 tokens | 结果 |
|---|---:|---:|---|
| Planner | 593 | 1,200 | 输出被截断，Run 失败 |

随后在 openJiuwen Adapter 中加入：

```json
{"thinking": {"type": "disabled"}}
```

并补充本地回归断言，确保结构化 Agent 请求始终关闭 DeepSeek 思考模式。相关回归测试 `9/9` 通过。

修正后的完整三 Agent 测试通过：

```text
0-2 小时：Alice 完成 design
2-6 小时：Alice 完成 build
第 6 小时：完成 delivery 里程碑
```

成功运行用量：

| 指标 | 数值 |
|---|---:|
| 输入 tokens | 2,184 |
| 输出 tokens | 298 |
| 总 tokens | 2,482 |

### 3.4 复杂三 Agent 项目规划测试

复杂任务文件：

```text
examples/project_planning/task_complex.json
```

任务包含：

- 3 名人员；
- 8 个工作项；
- 设计、后端、前端、文档、集成、测试和发布；
- 多条依赖关系；
- 后端、前端和文档并行执行；
- 人员技能与可用时间约束；
- 两个里程碑；
- 第 12 小时截止；
- 预算 2,500。

生成排期：

| 时间 | 人员 | 工作项 |
|---|---|---|
| 0-1 | Alice | requirements |
| 1-3 | Alice | architecture |
| 3-7 | Bob | backend |
| 3-6 | Carol | frontend |
| 3-5 | Alice | docs |
| 7-9 | Bob | integration |
| 9-11 | Carol | qa |
| 11-12 | Carol | release |

里程碑结果：

- `development-complete`：第 7 小时完成；
- `release-complete`：第 12 小时完成。

运行结果：

| 指标 | 数值 |
|---|---:|
| Run ID | `0abb1aa4-42a3-42f8-a639-c14e3055ee9c` |
| 状态 | `completed` |
| Agent 数量 | 3 |
| Tool 调用 | 0 |
| 重试 | 0 |
| 硬约束错误 | 0 |
| 总耗时 | 8.6768 秒 |
| 输入 tokens | 3,783 |
| 输出 tokens | 684 |
| 总 tokens | 4,467 |

各 Agent 用量：

| Agent | 输入 tokens | 输出 tokens | 合计 |
|---|---:|---:|---:|
| Planner | 938 | 97 | 1,035 |
| Executor | 1,397 | 577 | 1,974 |
| Critic | 1,448 | 10 | 1,458 |
| 合计 | 3,783 | 684 | 4,467 |

按测试时 DeepSeek Flash 官方价格估算，本次复杂运行费用约为人民币 0.005 元。实际扣费以 DeepSeek 控制台为准。

价格参考：<https://api-docs.deepseek.com/quick_start/pricing/>

## 4. Trace 记录

### 4.1 业务 Trace 数据库

复杂任务的持久化 Trace 位于：

```text
/Users/dlg/vscodeProjects/evoteam/traces/complex-planning-run.sqlite3
```

主要数据表：

- `events`：有序 TraceEvent；
- `runs`：完整 Task、Strategy、Agent 结果、评价和封存快照；
- `strategies`：本次使用的 Strategy 版本；
- `model_configs`：不含明文展示的模型绑定信息。

本次 Run 共记录 14 条事件：

| Sequence | Event | Node |
|---:|---|---|
| 0 | `task_created` | - |
| 1 | `team_created` | - |
| 2 | `agent_started` | planner |
| 3 | `agent_message` | planner |
| 4 | `agent_completed` | planner |
| 5 | `agent_started` | executor |
| 6 | `agent_message` | executor |
| 7 | `agent_completed` | executor |
| 8 | `agent_started` | critic |
| 9 | `agent_message` | critic |
| 10 | `agent_completed` | critic |
| 11 | `run_finished` | - |
| 12 | `evaluation_completed` | - |
| 13 | `run_sealed` | - |

可以使用 SQLite 查看事件索引：

```bash
sqlite3 traces/complex-planning-run.sqlite3 \
  "SELECT sequence, json_extract(data, '$.event_type'), json_extract(data, '$.node_id') FROM events WHERE run_id='0abb1aa4-42a3-42f8-a639-c14e3055ee9c' ORDER BY sequence;"
```

业务 Trace 中保存了：

- Task 和 Strategy 身份；
- Agent 实例身份；
- Agent 输入消息；
- 直属上游事件引用；
- Agent 结构化结果；
- 输入和输出 tokens；
- Run 状态、总耗时和评价；
- 事件之间的 `caused_by` 因果引用。

### 4.2 openJiuwen 原始模型日志

原始 LLM 日志位于：

```text
/Users/dlg/vscodeProjects/evoteam/logs/logs/llm.log
```

该日志包含：

- 完整 System Prompt；
- 发送给模型的消息；
- 模型原始回答；
- 模型名称和请求参数；
- Token usage；
- 调用开始和结束时间。

注意：该文件可能包含任务原文或业务数据，不能提交到 Git。当前 `.gitignore` 已排除整个 `logs/` 目录。

当前 SDK 日志使用 `default_trace_id`，尚未与 EvoTeam 的 `run_id` 正式关联。因此业务 Trace 与 SDK Trace 目前是两套记录。

## 5. 本次测试发现的问题

### 5.1 默认思考模式会耗尽短输出预算

DeepSeek V4 Flash 默认思考模式曾导致 Planner 在输出 JSON 前耗尽 1,200 tokens。当前已通过显式关闭思考模式解决，并有本地测试保护。

### 5.2 Executor 的说明文字存在算术矛盾

复杂任务排期的实际人工成本为：

```text
Alice: 5 * 120 = 600
Bob:   6 * 150 = 900
Carol: 6 * 130 = 780
总计: 2,280
预算余量: 220
```

但 Executor 的文字说明先后出现了 `2,400` 和 `2,410`。结构化排期本身正确，ConstraintChecker 根据排期重新计算后确认未超预算，因此最终硬约束评价通过。

这说明当前系统能检查结构化计划，但不能检查 `validation_notes`、`risks` 等自然语言说明是否与结构化数据一致。Critic 也没有发现该矛盾。

### 5.3 Agent 当前没有 Skill 和 Tool

三个 Agent 当前均为：

```json
{
  "skill_refs": [],
  "tool_policy": {
    "allowed_tools": [],
    "required_tools": []
  }
}
```

全局 `max_tool_calls=0`，openJiuwen Adapter 也会拒绝带有 Tool、Skill 或 Retry 的配置。

`evoteam/tools/constraint_checker.py` 是任务完成后由程序调用的 Evaluator 组件，不是 Agent 可以主动调用的 Tool。

### 5.4 Critic 不能触发返工

当前 `retry_limit=0`、`replan_limit=0`。即使 Critic 返回问题，固定 v0 也不会重新调用 Executor。Critic 目前主要产生审查记录，最终是否通过仍由确定性 Evaluator 判断。

### 5.5 已实现首版 Prompt 自演进闭环

当前已形成以下显式离线闭环：

```text
重复失败
  -> 聚合 Experience
  -> 归因
  -> 生成 Strategy Candidate
  -> 离线验证
  -> Gate 决策
  -> 晋级或拒绝
```

实现边界：首版只会把 Executor 的 `executor@v0` 替换为已登记的
`executor@v1-resource-check`，并在同一验证集上配对比较。Candidate 生成器不能读取验证集，
验证 Run 使用 `validation` 用途并单独封存，版本切换与 EvolutionRecord 在 SQLite 中原子落盘。
目前不会自动生成 Tool、扩大权限、改拓扑或自由修改代码；真实 DeepSeek 演进实验也尚未执行。

## 6. 下一步开发建议

### P0：接入两个确定性 Agent Tool

#### `calculate_schedule`

建议授权给 Executor，输入结构化排期，返回：

- 实际人工成本；
- 人员占用区间；
- 工作完成时间；
- 里程碑完成时间；
- 关键路径；
- 可用预算余量。

#### `validate_plan`

建议授权给 Critic，复用现有 ConstraintChecker，返回：

- 缺少工作项；
- 依赖顺序错误；
- 人员技能不匹配；
- 同一人员时间冲突；
- 超出人员可用时间；
- 超过项目期限或里程碑；
- 预算超限；
- 结构化结果和说明文字不一致。

建议权限：

| Agent | Tool |
|---|---|
| Planner | 暂时无 Tool |
| Executor | `calculate_schedule` |
| Critic | `validate_plan` |

验收标准：Trace 中出现 `tool_called` 和 `tool_result`；Agent 输出引用真实 Tool 结果；工具调用数量受预算限制。

### P0：增加一次受控返工

建议流程：

```text
Planner
  -> Executor
  -> Critic + validate_plan
      -> 通过：Evaluator
      -> 失败：Executor 修正一次
                -> Critic 再检查
                -> Evaluator
```

建议限制：

- `replan_limit=1`；
- 模型调用禁止 SDK 自动重试；
- Tool 总调用上限 5；
- 保留全局 Token 与超时预算；
- 每次返工必须引用具体 issue 和 Tool evidence。

验收标准：准备一个故意包含资源冲突的首轮排期，系统能发现冲突、修正并在第二轮通过；Trace 能完整回放修改前后结果。

### P0：增加 Trace 查询 API

建议增加：

```text
GET /v1/runs
GET /v1/runs/{run_id}
GET /v1/runs/{run_id}/events
```

接口应支持根据 Run ID 查询：

- Agent 输入与输出；
- Tool 调用和结果；
- Token 和耗时；
- 返工原因；
- 最终评价；
- 事件因果关系。

同时把 EvoTeam `run_id` 注入 openJiuwen 日志上下文，使业务 Trace 和 SDK Trace 可以关联。

### P1：建立小型评测集

先建立 20-50 个确定性项目规划案例，覆盖：

- 正常串行计划；
- 可并行工作；
- 人员技能不足；
- 人员时间冲突；
- 预算不足；
- 不可满足的截止时间；
- 多里程碑；
- 依赖链和依赖分支；
- 自然语言说明与结构化数据矛盾。

每个案例提供输入、可行性标签和可由程序验证的期望约束，不要求只有唯一排期答案。

### P1：实现最小 Prompt 自演进

初版只允许演进 Prompt，不允许模型任意修改 Team、权限或运行时代码。

建议闭环：

1. 监控相同 Strategy 的历史 Run；
2. 连续出现同类错误时生成 FailureExperience；
3. 归因到特定 Agent 和 Prompt；
4. 生成新 Prompt Candidate；
5. 在固定评测集上同时运行 Current 与 Candidate；
6. 比较成功率、硬约束错误、Token 和耗时；
7. Gate 达标后进入人工确认；
8. 人工确认后晋级，否则拒绝并保留证据。

建议第一种演进目标就是本次发现的成本说明错误：让 Executor 在输出前调用计算工具，并要求所有成本说明引用 Tool 结果。

### P2：Trace 可视化

在查询 API 稳定后再增加简单页面，以时间线展示：

```text
Task Created
Planner Completed
Executor Called calculate_schedule
Executor Completed
Critic Called validate_plan
Critic Requested Revision
Executor Revised
Evaluation Completed
Run Sealed
```

不建议现阶段优先增加更多角色、向量数据库、浏览器工具或复杂前端。先把 Tool、返工、Trace 和最小演进闭环做实，更能证明 EvoTeam 的核心价值。

## 7. 推荐的下一版 Demo 验收目标

下一版可以定义为 `v0.2 Tool + Repair`，满足以下条件即算完成：

- DeepSeek 三 Agent 链路稳定运行；
- Executor 至少能调用一个计算 Tool；
- Critic 至少能调用一个校验 Tool；
- 错误计划能自动返工一次；
- 所有 Tool 调用和返工过程进入 Trace；
- 可通过 HTTP API 查询完整 Run；
- 固定评测集不少于 20 个案例；
- 输出成功率、硬约束错误、Token、耗时四项指标；
- API Key、任务原文和模型日志具有明确的脱敏与保留策略。

完成 `v0.2` 后，再进入 `v0.3 Prompt Evolution`，实现受约束的候选生成、离线对比、Gate 和人工晋级。

## 8. 2026-09-09 最新版本 DeepSeek 真实回归

本节记录完成受限 DAG、一次 Critic 返工、新增 Verifier Candidate、多候选比较和完整演进产物持久化后的真实回归。测试使用 `deepseek-v4-flash / api-2026-09`，关闭思考模式，未启用 Tool 或 Skill。

测试产物位于：

```text
runs/real_regression_20260909_v2/
```

### 8.1 测试规模

| 指标 | 数值 |
| --- | ---: |
| Team Run | 6 |
| Online Run | 2 |
| Validation Run | 4 |
| 真实模型调用 | 21 |
| 总 tokens | 21,276 |
| Team 延迟合计 | 43.522 秒 |
| Tool 调用 | 0 |

DeepSeek 接口没有返回费用字段，因此只记录 token，不把估算价格当作实际扣费。

### 8.2 复杂可行任务

- Run ID：`2383d4b3-734f-419c-9315-54915c09a178`
- 执行链：Planner → Executor → Critic
- 状态：completed
- 规则评价：success=true
- 硬约束错误：0
- tokens：4,879
- 延迟：9.180 秒
- retry_count：0

该任务由 Critic 一次通过，因此没有为了展示功能而强制返工。

### 8.3 Critic → Executor 一次有界返工

故意不可行任务要求 6 小时工作在 4 小时期限、4 小时人员可用时间和只能支付 4 小时的预算内完成。

- Run ID：`ffef4cc8-9774-43ba-ae65-c60c5133c30a`
- 实际执行链：Planner → Executor → Critic → Executor → Critic
- tokens：5,077
- 延迟：12.622 秒
- agent_count：5
- retry_count：1

第一次 Critic 返回 `passed=false`，指出排期只覆盖 4 小时、缺少剩余 2 小时的处理方案。第二次 Executor 的输入中真实包含 `critic_feedback` 以及对应 `source_event_ids`，并补充了延长期限、增加人员或增加预算等建议。由于输入本身不可行，第二次 Critic 仍未通过，独立 Evaluator 最终正确报告一个 `duration_mismatch`，系统没有把“解释得更完整”伪装成任务成功。

### 8.4 Monitor 与两个演进候选

本轮专用 Policy 使用 `min_samples=1`、`repeated_failure_threshold=1`、`max_candidates=2`，只用于验证机制，不作为正式实验阈值。Monitor 从上述失败 Run 生成 `repeated_failure` Trigger，随后系统生成：

1. `project-planning@1`：`UPDATE_PROMPT`，将 Executor 更新为 `executor@v1-resource-check`。
2. `project-planning@2`：`ADD_AGENT_CONFIG`，新增 `verifier@v0`。

失败归因、两个 MutationProposal、两份 ValidationResult、两份改进归因和最终 EvolutionRecord 均可从 SQLite 完整读取。

### 8.5 配对验证与真实 Verifier DAG

| Candidate | Current tokens | Candidate tokens | Current latency | Candidate latency | 成功状态 | Gate |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Prompt v1 | 2,681 | 2,612 | 6.909s | 4.605s | 两边均成功 | FAIL |
| Verifier v2 | 2,771 | 3,256 | 5.190s | 5.015s | 两边均成功 | FAIL |

Verifier Candidate 的真实执行顺序为：

```text
Planner → Executor → Verifier → Critic
```

Trace 证明 Critic 的 `upstream` 同时包含 `executor` 原计划和 `verifier` 的 `{passed: true, issues: []}`，并持有两条上游完成事件引用。它不是只写入配置而没有真正调用模型的“纸面 Agent”。

### 8.6 Gate 与生命周期结果

- Prompt Candidate 的 token 降低 69（约 2.57%），延迟降低约 33.35%，但当前 Gate 不把纯效率改善视作正向收益，因此以“未达到任何预注册的正向收益条件”拒绝。
- Verifier Candidate 的 token 增加约 17.50%，超过 10% 上限，因此拒绝。
- 最终状态为：v0=CURRENT，v1=REJECTED，v2=REJECTED，没有不满足 Gate 的版本被错误上线。

本轮暴露出的首要问题是 Gate 规则口径不完整：它会限制 token/延迟回归，却没有允许“质量不退化且效率显著改善”的效率型 Candidate 晋级。正式实验前应增加候选目标类型、最小效率收益阈值以及足够样本下的稳定性判断。

### 8.7 本地代码回归

真实模型实验结束后重新执行完整测试：

```text
85 passed, 1 skipped, 22 warnings
```

Warning 来自 Starlette、openJiuwen 等依赖的弃用提示。本轮没有修改业务代码。

最新版本与最初 GitHub 提交的详细差异见 `docs/VERSION_COMPARISON.md`。
