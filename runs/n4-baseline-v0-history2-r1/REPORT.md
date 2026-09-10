# N4 固定 v0 History 基线报告

## 实验身份

- 实验：`n4-baseline-v0-history2-r1`
- 代码提交：`c1204d3d60ad2bb097bdbdd612b896ba85e6a780`
- 数据：`project-planning-manifest@2` / `project-planning-history@2`
- Strategy：`project-planning@0`
- 模型：`deepseek-v4-flash@api-2026-09`
- 推理参数：temperature `0`、top_p `1`、单次最大输出 `4096 tokens`、超时 `60s`
- 任务：6 道，1 次重复；请求硬上限 18，实际发起 17
- seed：Runtime 不支持，未应用
- 候选比较：关闭
- Final Test：关闭

完整输入摘要、Prompt 引用、预算、Run ID 和逐 Run 指标见 `baseline_report.json`；完整快照与 Trace 事件位于本地 `evidence.db`，数据库不纳入 Git。

## 结果摘要

| 范围 | 成功数/总数 | 成功率 | 硬约束错误 |
| --- | ---: | ---: | ---: |
| 全部 | 5/6 | 83.3% | 1 |
| resource_conflict | 2/3 | 66.7% | 1 |
| dependency | 3/3 | 100% | 0 |

唯一失败是 `history-resource-conflict`。Planner 成功后，Executor 请求遇到一次连接错误；该 Run 没有唯一计划产物，因此确定性 Evaluator 记录 `missing_or_ambiguous_plan`。系统没有重试，也没有把失败样本排除。

## 成本与运行指标

- 17 次模型调用：16 次成功，1 次连接失败。
- 5 条 Token 完整的成功 Run 合计 `19,895` tokens；失败 Run 用量未知，因此全批 Token 总数保持未知，不能把缺失值记为零。
- 延迟 P50：`6.029s`；P95：`9.292s`，nearest-rank，样本数 6。样本远少于 20，只作描述性记录。
- 超时：0。
- 返工/Retry：0。
- Tool 调用：0。
- API 没有返回费用字段，因此本报告不能给出可信人民币成本；需要以 DeepSeek 账户账单为准。

## Trace 与证据

SQLite `events` 表共保存：

- `task_created` 6 条
- `team_created` 6 条
- `agent_started` / `agent_message` 各 17 条
- `agent_completed` 16 条
- `agent_failed` 1 条
- `evaluation_completed`、`run_finished`、`run_sealed` 各 6 条

六条 Run 均已封存。SDK 原始日志位于本地 `logs/logs/`，可能包含完整任务和模型输出，按 `.gitignore` 不提交。

## 结论与限制

本批说明固定 v0 在五道结构化规划题上生成了满足确定性规则的计划，同时证明网络错误会作为真实失败进入基线。当前样本只有每类三题且只运行一次，不能据此声称 v0 成功率稳定，也不能直接设定统计显著性门槛。

基于本批冻结 `project-planning-monitor@n4-baseline-c1204d3`：窗口与最小样本均为 6，同一确定性错误至少跨 2 个 Run 重复才触发，冷却期为 6 个新 Run。唯一连接错误不满足重复失败条件，因此不应启动候选生成。

实际 Monitor 观察结果为 `sample_count=6`、`reason=未达到重复失败阈值`、`trigger=null`，见 `monitor_result.json`。该观察不调用模型。

当前数据不足以从波动中校准正式 Gate Policy，故本批不伪造 Gate 阈值。候选比较最多使用既有 Validation 两题做机制验证，并明确标注样本不足；不得为了获得 PASS 而降低“成功题退化即失败”的安全规则。
