# EvoTeam × DeepSeek V4 Flash 真实执行与自演进记录

测试时间：2026-09-09（Asia/Shanghai）

模型：`deepseek-v4-flash` / `api-2026-09`

模型参数：temperature=0、top_p=1、thinking disabled、ReAct 上限 3、无 Tool
数据库：`runs/real_evolution_20260909/evoteam.db`

## 1. 调用与用量

共进行 6 个 Team Run，每个 Run 按 Planner → Executor → Critic 调用 3 次模型：

- 真实复杂任务：1 Run / 3 次调用 / 4611 tokens
- 不可行诊断历史：3 Run / 9 次调用 / 7980 tokens
- Current/Candidate 配对验证：2 Run / 6 次调用 / 5232 tokens
- 合计：18 次模型调用 / 17823 tokens

供应商费用未进入返回协议，因此数据库中的 cost 为 null；不能用 token 数伪造人民币费用。

## 2. 真实复杂任务执行

Run ID：`5a63548a-abb5-491c-bc17-6ab081f0b159`

Strategy：`project-planning@0`
结果：COMPLETED，规则评价通过，0 个硬约束错误，4611 tokens，8.590 秒。

### Planner

识别了 12 小时期限、2500 预算、人员可用时间、依赖与里程碑。用量为 938 input + 64 output tokens。

### Executor

生成了 8 个工作项的完整排期：

| 工作项 | 人员 | 时间 |
| --- | --- | --- |
| requirements | alice | 0–1 |
| architecture | alice | 1–3 |
| backend | bob | 3–7 |
| frontend | carol | 3–6 |
| docs | alice | 3–5 |
| integration | bob | 7–9 |
| qa | carol | 9–11 |
| release | carol | 11–12 |

两项里程碑分别在 hour 7 和 hour 12 完成。Executor 用量为 1364 input + 624 output tokens。

### Critic 与独立评价

Critic 返回 `passed=true`，用量为 1611 input + 10 output tokens。Team 外的 ConstraintChecker 独立复核依赖、人员技能、资源重叠、期限、预算与里程碑，结果为 0 个错误。

### Trace 时间线

```text
0 task_created
1 team_created
2 planner agent_started
3 planner agent_message
4 planner agent_completed
5 executor agent_started
6 executor agent_message
7 executor agent_completed
8 critic agent_started
9 critic agent_message
10 critic agent_completed
11 run_finished
12 evaluation_completed
13 run_sealed
```

## 3. 重复失败历史

诊断任务故意设置为不可行：build 要求 6 小时，但 alice 只在 0–4 可用，deadline=4，预算也只覆盖 4 小时。

| Run | Tokens | 延迟 | 规则错误 |
| --- | ---: | ---: | --- |
| `e08ac62e-...` | 2653 | 8.469s | duration_mismatch |
| `fc1be45c-...` | 2732 | 7.844s | duration_mismatch |
| `b394c02f-...` | 2595 | 6.106s | duration_mismatch |

三次中 Planner 都识别了不可行，Critic 也指出无法交付；但 Executor 为满足 deadline，仍把 6 小时工作写成 0–4 的 4 小时排期。规则评价器因此稳定检测到 `duration_mismatch`。

另一个观察是模型在自然语言中把 `budget_minor` 写成“元”。比较数值仍正确，但金额单位表述不严谨，应在后续 Prompt 和 Schema 中加强。

## 4. Monitor Trigger

Monitor 在 4 个 online Run 的窗口中发现 `duration_mismatch` 出现 3 次，产生：

- Trigger Type：`repeated_failure`
- Trigger ID：`trigger-5735808a9ff75cb57335984a16d161fc4e867df8babaae97c4ad0ff5d3aef18e`
- Evidence：三个失败 Run ID
- Current：`project-planning@0`

## 5. 自演进过程

### 5.1 Failure Attribution

确定性规则将计划硬约束错误归因为：

- Origin：Executor，confidence=1.0；错误首先进入项目计划产物。
- Control：Critic，confidence=0.8；Critic 位于计划之后，但线上结果仍未通过独立评价。

Attribution Ref：`failure-attribution-e306700787d8814aab6d3d5617c9f819a6e31e62ae49a1934f10a6e91b254f29`

### 5.2 Mutation 与 Candidate

系统只执行登记过的白名单修改：

```text
operation: UPDATE_PROMPT
target: executor
before: executor@v0 / config_version=0
after:  executor@v1-resource-check / config_version=1
candidate: project-planning@1
parent: project-planning@0
```

新 Prompt 要求 Executor 在输出前显式核对技能、可用时间、持续时间、依赖、人员占用区间、成本、期限和里程碑。不增加 Tool，不改变模型，不改变拓扑或权限。

### 5.3 Current/Candidate 配对验证

两边使用同一个 `validation-resource-sequence` 任务、同一个模型、Evaluator 和预算。

| 指标 | Current v0 | Candidate v1 | 差值 |
| --- | ---: | ---: | ---: |
| 成功 | true | true | 相同 |
| 硬约束错误 | 0 | 0 | 相同 |
| Tokens | 2440 | 2792 | +352 / +14.426% |
| 延迟 | 6.035s | 4.834s | -1.201s / -19.9% |
| Agent 数 | 3 | 3 | 相同 |
| Tool Calls | 0 | 0 | 相同 |

两边生成的排期相同：design 0–2，build 2–6，均通过规则评价。Candidate 的说明更完整，但当前 Evaluator 不给语义质量分，因此这部分不能计为已验证收益。

### 5.4 Validation Gate

Gate Policy：Token 最大允许增幅 10%，延迟最大允许增幅 25%，不允许质量回归。

实际 Token 增幅 14.426%，超过上限。Gate Decision：`FAIL`。

### 5.5 Lifecycle

```text
project-planning@0: CURRENT
project-planning@1: REJECTED
serving pointer: project-planning@0
```

Candidate 没有上线。策略定义、验证 Run、Gate 理由和 EvolutionRecord 均保存在 SQLite。

## 6. 结论

这次真实实验同时证明了两件事：

1. 固定三 Agent 可以在复杂可行任务上生成通过确定性检查的计划。
2. 自演进闭环不会因为出现 Trigger 就强行更新策略；没有达到 Gate 的 Candidate 会被拒绝，Current 保持不变。

本次不能证明新 Prompt 优于旧 Prompt。验证集只有一个简单样本，且触发失败来自不可行任务。下一轮应使用 5–10 个可行但容易产生资源/依赖错误的 History 样本，以及独立的多样化 Validation 样本，再校准 Token Gate。

## 7. 原始记录

- `history_1.json`、`history_2.json`、`history_3.json`：三个真实失败 SealedRun
- `history_1.log`、`history_2.log`、`history_3.log`：openJiuwen/DeepSeek 原始 SDK 日志
- `monitor.json`：MonitorResult 与 Trigger
- `evolution.json`：EvolutionRecord 与 GateResult
- `evolution.log`：Current/Candidate 两个真实验证 Run 的 SDK 日志
- `evoteam.db`：完整 Task、Strategy、RunSnapshot、TraceEvent、Evaluation 与治理记录
