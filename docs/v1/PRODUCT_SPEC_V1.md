# EvoTeam Product Spec V1

> 状态：V1 FROZEN  
> 冻结范围：产品机制、核心抽象、演进闭环、系统边界。  
> 未冻结范围：触发阈值、验证集规模、Promotion 具体阈值、搜索预算等实验参数。

## 1. 产品定义

EvoTeam 是一个：

> **基于 openJiuwen Core 的经验驱动、自演进多智能体组织与协作系统。**

核心思想：

> **任务决定 Team 的初始组织，经验决定 Team 的下一代组织。**

EvoTeam 的目标不是让 Agent 数量不断增加，而是在：

- 任务质量
- 成本
- 延迟
- Agent 数量
- 通信复杂度

之间寻找更合适的组织 Strategy。

## 2. 核心产品用户

- AI Agent Developer
- Researcher
- AI Application Team

EvoTeam 当前不是面向普通用户的聊天产品，而更接近：

```text
Agent Organization Lab
+
Evolution Engine
+
Evaluation Console
```

## 3. 核心抽象

### Role

表示“你是谁”。

V1 固定基础 Role Pool：

- Planner / Coordinator
- Researcher
- Analyst / Executor
- Writer / Synthesizer
- Verifier
- Critic / Reviewer

### Skill

表示“你会什么”。

例如：

- web-research
- paper-research
- statistical-analysis
- citation-verification
- timeline-analysis

### Tool

表示“你能操作什么”。

例如：

- Web Search
- Python
- Database
- Calculator
- File Reader

Tool 默认不是 Agent。

### Strategy

表示：

> 一支 Team 针对某类任务应该由谁组成、具备什么能力、如何通信与执行。

Strategy 包括：

```text
Team Composition
Role Configuration
Skill Configuration
Tool Policy
Prompt Policy
Team Topology
Execution Policy
Retry / Replan Policy
```

Strategy 是 EvoTeam V1 的核心演进单元。

## 4. Task-Driven Team

EvoTeam 采用：

> **Task-Driven Team, Role-Based Agents**

不是：

```text
NewsReportAgent
AcademicReportAgent
DataAnalysisAgent
PlanningAgent
```

而是：

```text
Task
 ↓
Task Analyzer
 ↓
Task Signature
 ↓
Strategy Select / Build
 ↓
Multi-Agent Team
 ↓
Execute
```

Task Family / Strategy Variant 不是 Agent 类型。

## 5. Task Signature

Task Analyzer 将自然语言任务转为结构化描述，例如：

```json
{
  "family": "report",
  "domain": "academic",
  "needs_search": true,
  "source_type": "paper",
  "freshness_sensitive": false,
  "needs_citation": true,
  "needs_numeric_analysis": false,
  "risk_level": "medium"
}
```

用于：

- Strategy Routing
- Capability Matching
- Variant Selection
- Initial Team Formation

## 6. Strategy Family

V1 采用：

> **Strategy Family + Specialized Variant**

例如：

```text
Strategy Library
│
├── Report
│   ├── General
│   ├── News
│   └── Academic
│
├── DataAnalysis
│   ├── Tabular
│   └── Statistical
│
└── Planning
    ├── Project
    └── ResourceConstraint
```

不维护一个全局万能 Strategy，也不为每个任务永久创建一个 Strategy。

## 7. Base + Variant Delta

子 Strategy 不完整复制父 Strategy。

```text
Effective Strategy
=
Parent Base Strategy
+
Variant Delta
```

例如 Academic Report 只增加：

```text
+ paper-search
+ citation-verification
+ academic-writing-policy
```

## 8. Variant 生命周期

首次出现的新需求不立即成为永久分支：

```text
AD_HOC
 ↓
CANDIDATE_VARIANT
 ↓
PERSISTENT_VARIANT
```

只有当某类需求重复出现，并且 Specialized Variant 在该子分布上经过验证确实优于 Parent，才成为长期 Variant。

## 9. Specialization 与 Generalization

### 向下：Specialization

当某类 Task Signature：

- 重复出现；
- 能力需求明显不同；
- Parent Strategy 持续表现不足；
- Specialized Candidate 在该子分布显著更好；

形成子 Variant。

### 向上：Generalization

如果某个子 Variant 的改进在多个兄弟 Variant 上也有效，则：

```text
Child Improvement
 ↓
Cross-Variant Validation
 ↓
Promote to Parent
```

V1 不实现复杂 Sibling Merge。

## 10. Strategy Freeze

如果：

- 连续多个 Candidate 无显著提升；
- 连续若干代提升低于阈值；
- Evolution Budget 达到上限；

则 Strategy 进入：

```text
FROZEN
```

出现新的失败模式、任务分布变化或新能力后再 UNFREEZE。

## 11. Experience 粒度

三层：

```text
Event = 观察单位
Run   = 学习单位
Window= 演进单位
```

### Event

实时记录：

```text
AGENT_STARTED
AGENT_MESSAGE
TOOL_CALLED
TOOL_RESULT
AGENT_COMPLETED
EVALUATION
```

### Run

Task 完成、失败、取消或超时后：

```text
Run → SEALED
```

形成结构化 Experience。

### Evolution Window

聚合多个同 Family Run，用于判断是否出现稳定 Failure Pattern。

## 12. Memory 与 Evolution

> **Memory 记录过去，Evolution 改变未来。**

Memory 存储：

- Task
- Strategy
- Trace
- Outcome
- Metrics
- Failure Tags

Evolution 进一步执行：

```text
Diagnosis
Attribution
Mutation
Validation
Promotion / Reject
```

## 13. Evolution Trigger

V1 Trigger 包括：

- Repeated Failure
- Performance Drift
- Negative Feedback
- High Cost
- High Latency
- Low Agent Contribution
- Tool Failure Pattern
- Constraint Violation Pattern

同时具备：

- Cooldown
- Evolution Budget
- Plateau Detection

## 14. Failure Attribution

Failure Attribution 回答：

> **应该改哪里？**

候选 Attribution Target：

```text
Agent / Role
Prompt
Skill
Tool
Edge
Topology
Execution Policy
```

V1 采用：

```text
Deterministic Evidence
+
Trace / Provenance Evidence
+
LLM Attribution
```

而不是单纯让一个 LLM 猜责任。

### 多因 Attribution

区分：

- Origin Failure：谁产生错误
- Control Failure：为什么错误没有被阻止

例如：

```json
{
  "failure": "numeric_error",
  "causes": [
    {
      "type": "origin",
      "target": "analyst",
      "confidence": 0.92
    },
    {
      "type": "control_failure",
      "target": "verifier",
      "confidence": 0.81
    }
  ]
}
```

## 15. Attribution Confidence

概念上：

```text
High Confidence   → 自动进入 Evolution
Medium Confidence → 多 Candidate 验证
Low Confidence    → NEEDS_MORE_EVIDENCE
```

具体阈值由实验决定。

## 16. Mutation Search

V1 使用：

> **Schema-Constrained Typed Mutation**

允许：

```text
PROMPT_UPDATE

SKILL_ADD
SKILL_REMOVE

TOOL_ADD
TOOL_REMOVE

ROLE_ADD_EXISTING
ROLE_REMOVE

EDGE_ADD
EDGE_REMOVE

MAKE_PARALLEL
MAKE_SEQUENTIAL

MAKE_CONDITIONAL

CHANGE_RETRY_POLICY
CHANGE_REPLAN_POLICY
```

暂不允许：

```text
CREATE_ARBITRARY_ROLE
FREEFORM_CODE_WORKFLOW
UNBOUNDED_LOOP
OPEN_ENDED_CROSSOVER
EVOLUTION_ENGINE_SELF_MODIFICATION
```

## 17. Minimal Mutation

一次 Candidate 尽量只改一个核心因素。

例如：

```text
Candidate A：只改 Analyst Prompt
Candidate B：只强制 Python Tool
Candidate C：只增加 Numeric Verifier
```

便于：

- Attribution
- Ablation
- Explainability
- Rollback
- PPT 展示

## 18. Candidate 数量

一次 Evolution Event 推荐生成：

```text
2 ~ 3 Candidates
```

通常分别来自不同层级：

- Prompt
- Tool / Skill
- Team / Topology

## 19. Validation Funnel

Candidate 不直接跑完整验证集：

```text
Mutation Proposal
 ↓
Static Validation
 ↓
Smoke Test
 ↓
Mini Validation
 ↓
Full Validation
 ↓
Promotion Decision
```

## 20. Validation Gate

大白话定义：

> **新旧 Strategy 做同一套考试，只有收益足够大且代价可接受，新 Strategy 才能换代。**

Validation 指标分为：

### Quality

- Success Rate
- Accuracy
- Completeness
- Constraint Satisfaction
- Fact Correctness

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

## 21. Promotion Policy

V1 优先采用：

```text
Hard Constraints
+
Minimum Improvement
+
Budget Guardrails
```

例如：

```text
Success Rate 不下降
Quality 至少提升 X%
Cost 增长不超过 Y%
Latency 增长不超过 Z%
```

X/Y/Z 由实验确定。

## 22. 两类 Promotion

### Quality-Oriented

质量明显提升，成本可控。

### Efficiency-Oriented

质量基本不变，但成本、延迟或复杂度显著下降。

因此 EvoTeam 同时支持：

```text
Growth
+
Pruning
```

## 23. Team Topology Evolution

允许：

- Add Verification Step
- Remove Low-value Step
- Add / Remove Edge
- Sequential ↔ Parallel
- Conditional Branch
- Retry / Replan Policy

不允许无约束无限循环或完全图。

> **V1 Team Evolution 是受 Schema 约束的 Graph Transformation。**

## 24. Verifier / Evaluator / Attribution

### Verifier

属于任务 Team，检查当前结果是否有错。

### Evaluator

属于系统评价层，判断整个 Strategy 表现如何。

Evaluator 可以由规则、Ground Truth、Unit Test、Metric Calculator、LLM Judge 组合。

### Attribution

任务失败后判断应该改哪里。

## 25. 与 openJiuwen 的边界

openJiuwen Core 负责：

```text
Agent Runtime
Model
Tool
Workflow / ReAct Primitive
```

EvoTeam 负责：

```text
Task Analysis
Strategy Library
Team Formation
Orchestration
Evaluation
Experience
Attribution
Evolution
Validation
Promotion / Rollback
```

JiuwenSwarm 作为 Related Work、Reference Implementation、Potential Baseline。

## 26. Benchmark Domains

V1 三类：

- Report Generation
- Data Analysis
- Task Planning

它们用于证明组织演进机制的泛化能力，不是三个独立产品。

## 27. 核心创新候选

1. Task-Adaptive Team Formation
2. Experience-Driven Strategy Evolution
3. Evidence-Based Failure Attribution
4. Validation-Gated Reversible Evolution
5. Complexity-Aware Organization Evolution

## 28. Evolution Governance

EvoTeam 的产品差异化概念：

> **自演进不仅要会修改，还要能够治理修改。**

系统必须回答：

```text
为什么要变？
依据是什么？
改了什么？
有哪些 Candidate？
验证成绩如何？
为什么 Promote / Reject？
能否 Rollback？
何时 Freeze？
```

## 29. V1 核心论点

> **任务决定初始组织。**

> **证据决定问题归因。**

> **验证决定组织是否换代。**

> **Memory 记录过去，Evolution 改变未来。**
