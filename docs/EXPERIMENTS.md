# EvoTeam 实验设计

> EvoTeam 的竞争力最终必须由实验支撑。

---

# 1. 为什么实验是核心

赛题要求明确包含：

```text
优化前 vs 优化后
```

因此项目不能只展示：

```text
一个成功 Case
```

而需要证明：

> 系统经过演进后，在一组任务上产生了稳定、可解释的收益。

---

# 2. 核心实验问题

## E1

固定 Team 和动态 Team 哪个更好？

## E2

Prompt Evolution 是否真正提升质量？

## E3

Tool Policy Evolution 是否提升正确性或降低成本？

## E4

Team Evolution 是否真的比简单增加 Agent 更有效？

## E5

演进是否会过拟合某几个历史任务？

## E6

Candidate Validation / Rollback 是否能阻止负向演进？

---

# 3. 三类任务

## 3.1 报告生成

任务特点：

- 信息组织；
- 搜索；
- 事实一致；
- 结构化输出。

候选指标：

```text
Completeness
Fact Accuracy
Citation Coverage
Structure Quality
```

---

## 3.2 数据分析

任务特点：

- 数值；
- 代码；
- 解释；
- 结论。

候选指标：

```text
Calculation Accuracy
Metric Coverage
Insight Quality
Consistency
```

---

## 3.3 任务规划

任务特点：

- 约束；
- 资源；
- 时间；
- 风险。

候选指标：

```text
Constraint Satisfaction
Feasibility
Coverage
Risk Quality
```

---

# 4. Baseline

至少需要：

## Baseline A：Single Agent

```text
一个通用 Agent
```

目的：

回答：

> 多 Agent 是否真的必要？

---

## Baseline B：Fixed Multi-Agent

例如：

```text
Planner
Executor
Critic
```

目的：

回答：

> 动态组织是否比固定 Workflow 更好？

---

## Baseline C：Multi-Agent + Retry

目的：

回答：

> “失败后重做”是否已经足够？

---

# 5. EvoTeam Variant

候选消融：

| Variant | Prompt Evo | Tool Evo | Team Evo |
| --- | --- | --- | --- |
| V0 | ❌ | ❌ | ❌ |
| V1 | ✅ | ❌ | ❌ |
| V2 | ✅ | ✅ | ❌ |
| V3 | ✅ | ✅ | ✅ |

这样可以回答：

> 到底是哪一种演进贡献了收益？

---

# 6. 核心指标

建议至少保留：

```text
Quality
Success Rate
Token Usage
Latency
Agent Count
Retry Count
```

可以构造综合目标：

```text
Reward =
Quality
- Cost Penalty
- Latency Penalty
```

注意：

具体权重目前 **[待定]**。

---

# 7. Before / After 设计

不要：

```text
拿一个 Before Case
再挑一个 After Case
```

正确方向：

```text
Train / History Tasks
        ↓
Evolution
        ↓
Held-out Validation Tasks
```

对：

```text
Strategy v1
Strategy v2
```

使用同一验证集合。

---

# 8. Evolution 记录

每一次演进应该留下：

```json
{
  "trigger": "...",
  "evidence": {},
  "mutation": "...",
  "before_strategy": "...",
  "candidate_strategy": "...",
  "validation_before": 0.0,
  "validation_after": 0.0,
  "decision": "promote_or_rollback"
}
```

这样未来 PPT 可以直接展示。

---

# 9. Team Evolution 示例实验

Generation 0：

```text
Planner
Executor
Critic
```

失败统计：

```text
numeric_error: 42%
```

Candidate：

```text
Planner
Executor
CodeVerifier
Critic
```

比较：

```text
Quality
Numeric Accuracy
Cost
Latency
```

如果收益不够：

```text
Rollback
```

---

# 10. “裁员”实验

非常重要的一个候选展示。

如果：

```text
RiskAgent
```

长期：

```text
Quality Gain < 1%
Token + 15%
Latency + 12%
```

系统提出：

```text
Remove RiskAgent
```

验证：

```text
Quality almost unchanged
Cost significantly lower
```

可以证明：

> Evolution != 不断增加 Agent。

---

# 11. 重复性

最终实验脚本应该支持：

```bash
uv run python scripts/evaluate.py ...
```

并输出固定格式结果。

至少：

- 固定模型版本；
- 固定数据集；
- 固定随机参数；
- 保存 Prompt 版本；
- 保存 Strategy；
- 保存运行 Trace。

---

# 12. PPT 中最终应出现的实验图

候选：

1. Before vs After 柱状图；
2. Generation Score 曲线；
3. Token / Quality Pareto；
4. Agent Count vs Quality；
5. Failure Tag 分布；
6. Strategy Evolution Timeline；
7. Ablation Table。
