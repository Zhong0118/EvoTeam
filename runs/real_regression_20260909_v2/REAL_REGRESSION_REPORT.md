# EvoTeam × DeepSeek V4 Flash 真实回归报告

测试日期：2026-09-09（Asia/Shanghai）

模型：`deepseek-v4-flash` / `api-2026-09`
测试范围：复杂任务、Critic 有界返工、Monitor Trigger、Prompt/Verifier 多候选演进、完整持久化与生命周期。

## 1. 总览

- Team Run：6 次（online 2 次，validation 4 次）
- 真实模型调用：21 次
- 总 tokens：21,276
- Team 延迟合计：43.522 秒
- Tool 调用：0
- API 未返回费用字段，因此不估算或伪造实际人民币费用。

## 2. 在线任务

### 复杂可行任务

- Run ID：`2383d4b3-734f-419c-9315-54915c09a178`
- 结果：completed / success=true
- 硬约束错误：0
- tokens：4,879
- 延迟：9.180 秒
- 执行顺序：Planner → Executor → Critic
- Critic 一次通过，retry_count=0。

### 故意不可行任务

- Run ID：`ffef4cc8-9774-43ba-ae65-c60c5133c30a`
- 结果：completed / success=false
- 硬约束错误：1（`duration_mismatch`）
- tokens：5,077
- 延迟：12.622 秒
- 执行顺序：Planner → Executor → Critic → Executor → Critic
- retry_count=1，证明 Critic 反馈被传给 Executor，且只返工一次。
- 第二次 Executor 明确补充了“剩余 2 小时无法安排”、延长期限、增加人员和增加预算建议；任务本身不可行，因此独立 Evaluator 仍正确判定失败。

## 3. Trigger 与演进

Monitor 在 2 个 online Run 中发现一次 `duration_mismatch`，按本次专用测试 Policy（阈值 1）生成 `repeated_failure` Trigger。

生成两个单因素 Candidate：

1. `project-planning@1`：Executor Prompt 更新为 `executor@v1-resource-check`。
2. `project-planning@2`：增加 `verifier@v0` AgentConfig。

归因、两个提案、两份验证结果、两个改进归因及最终 EvolutionRecord 均已写入 SQLite。

## 4. 配对验证结果

| Candidate | Current tokens | Candidate tokens | Current latency | Candidate latency | 结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| Prompt v1 | 2,681 | 2,612 | 6.909s | 4.605s | Gate FAIL |
| Verifier v2 | 2,771 | 3,256 | 5.190s | 5.015s | Gate FAIL |

四个验证 Run 均通过任务规则，硬约束错误均为 0。

Verifier Candidate 的真实执行顺序为：

```text
Planner → Executor → Verifier → Critic
```

Trace 显示 Critic 的 `upstream` 同时包含 `executor` 与 `verifier`，并引用两个对应完成事件。Verifier 返回 `passed=true`。

## 5. Gate 与生命周期

- Prompt Candidate 的 token 降低 69（约 2.57%），延迟降低约 33.35%，但当前 Gate 不把纯 token/延迟改善认定为正向收益，因此以“未达到任何正向收益条件”拒绝。
- Verifier Candidate 的 token 增加约 17.50%，超过 10% 上限，因此拒绝。
- 最终没有 Candidate 晋升：v0=Current，v1/v2=Rejected。

这里暴露了一个明确的实现缺口：Gate 已限制效率回归，却还没有“效率型 Candidate 在质量不退化时可因效率收益 PASS”的规则。正式测试前应增加候选类型和最小效率收益阈值。

## 6. 回归检查

完整本地测试：`85 passed, 1 skipped`。22 条 warning 均来自 Starlette/openJiuwen 等上游依赖的弃用提示。

## 7. 产物位置

- `evoteam.db`：完整 Strategy、Run、Trace、Attribution、Proposal、Validation 和 EvolutionRecord
- `complex.json` / `complex.log`：复杂任务结果与 SDK 日志
- `infeasible.json` / `infeasible.log`：有界返工任务结果与 SDK 日志
- `monitor.json`：MonitorResult 与 Trigger
- `evolution.json` / `evolution.log`：多候选验证、Gate 和生命周期记录
- 其余 JSON：本轮冻结的 Strategy、Policy、ValidationPlan、GatePolicy 与任务输入
