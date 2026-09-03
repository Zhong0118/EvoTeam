# EvoTeam Experiments V1

## 1. 最终要证明什么

1. Multi-Agent 在复杂任务上比 Single Agent 有价值。
2. Dynamic Team 比固定 Team 更能适应异构任务。
3. 跨任务 Experience 能指导 Strategy Evolution。
4. Evidence-Based Attribution 比 LLM-only Attribution 更可靠。
5. Validation Gate 能阻止负向演进。
6. Pruning 能在基本保持质量时降低成本和复杂度。

## 2. 三类 Benchmark

### Report Generation

- Completeness
- Fact Correctness
- Citation
- Structure
- Freshness

### Data Analysis

- Calculation Accuracy
- Metric Coverage
- Insight Quality
- Consistency

### Task Planning

- Constraint Satisfaction
- Feasibility
- Risk Coverage
- Resource Reasonableness

## 3. Baselines

### B0 Single Agent

回答：

> 多 Agent 是否真的有必要？

### B1 Fixed Multi-Agent

例如：

```text
Planner → Executor → Critic
```

### B2 Fixed Multi-Agent + Retry

回答：

> Retry 是否已经足够？

### B3 Dynamic Team without Cross-task Evolution

回答：

> inference-time 动态组队与跨任务演进有什么区别？

### B4 EvoTeam

完整机制：

```text
Dynamic Team
+ Experience
+ Attribution
+ Mutation
+ Validation
```

## 4. Ablation

| Variant | Dynamic Team | Experience | Attribution | Prompt/Tool Evo | Team Evo | Validation |
| --- | --- | --- | --- | --- | --- | --- |
| V0 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| V1 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| V2 | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| V3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 5. 数据划分

```text
History Set
 ↓
发现 Failure Pattern
 ↓
Evolution

Validation Set
 ↓
Current vs Candidate
 ↓
Promotion

Test Set
 ↓
最终报告
```

## 6. Attribution 实验

构造：

- Prompt Defect
- Tool Failure
- Missing Verification
- Redundant Communication
- Incorrect Routing

比较：

```text
LLM-only
vs
Trace + LLM
vs
Rule + Trace + LLM
```

指标：

- Attribution Accuracy
- Top-k Recall
- Confidence Calibration

## 7. Strategy Family 实验

比较：

```text
One Global Strategy
vs
Base + Specialized Variant
```

观察：

- Quality
- Strategy Count
- Generalization
- Maintenance Complexity

## 8. Generalization 实验

某子 Variant 产生有效能力：

```text
Academic → Source Reliability Check
```

测试：

```text
Academic
News
General
```

如果普遍有效，则 Promote to Parent。

## 9. Pruning 实验

例如：

```text
Current:
Planner → Analyst → Critic → Verifier

Candidate:
Planner → Analyst → Conditional Verifier
```

如果：

```text
Quality ≈
Cost ↓
Latency ↓
```

则允许 Promote。

## 10. Validation Funnel

```text
Static
→ Smoke
→ Mini
→ Full
```

记录：

- Candidate Survival Rate
- Evolution Cost
- Token
- Latency

## 11. 核心指标

### Quality

- Task Score
- Success Rate
- Error Rate
- Constraint Satisfaction

### Efficiency

- Token
- Cost
- Latency
- Tool Calls

### Complexity

- Agent Count
- Edge Count
- Communication Rounds
- Retry Count

### Evolution

- Candidate Count
- Promotion Rate
- Rejection Rate
- Generation Gain
- Evolution Cost
- Time to Plateau
