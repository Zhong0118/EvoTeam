# EvoTeam Product Spec V1 — Draft

> 状态：DRAFT  
> 尚未冻结  
> 本文档用于把当前讨论收敛成一个可继续评审的产品规格。

---

# 1. Product Statement

EvoTeam 是一个：

> **基于 openJiuwen Core 的经验驱动、自演进多智能体组织与协作系统。**

核心思想：

> 任务决定 Team 的初始组织，经验决定 Team 的下一代组织。

---

# 2. Product User

Primary User：

```text
AI Agent Developer
Researcher
AI Application Team
```

EvoTeam 不优先面向普通聊天用户。

---

# 3. Product Object

核心对象：

```text
Task
Task Family
Role
Skill
Tool
Team
Strategy
Run
Trace
Evaluation
Experience
Evolution Proposal
Candidate
Generation
```

---

# 4. Core Abstractions

## Role

V1 固定池：

```text
Planner
Researcher
Analyst / Executor
Writer
Verifier
Critic
```

## Skill

角色可以加载的可复用能力。

## Tool

Agent 可调用外部能力。

## Strategy

定义：

```text
Team Composition
Skills
Tools
Prompts
Topology
Execution Policy
```

Strategy 是主要演进单元。

---

# 5. Task-driven Architecture

不是：

```text
一个 Task Family = 一个大 Agent
```

而是：

```text
Task
 ↓
Task Analyzer
 ↓
Strategy Select / Build
 ↓
Multi-Agent Team
 ↓
Execute
```

任务驱动 Team，Role-based Agent 负责协作。

---

# 6. Strategy Family

V1 推荐：

```text
ReportStrategy
DataAnalysisStrategy
PlanningStrategy
```

内部允许 Variant：

```text
Report
├── General
├── News
└── Academic
```

实现概念：

```text
Parent Base
+
Child Delta
```

避免完整复制。

---

# 7. Strategy Lifecycle

```text
DRAFT
 ↓
ACTIVE
 ↓
EVOLVING
 ↓
CANDIDATE
 ↓
VALIDATING
 ├── PROMOTED
 └── REJECTED
```

稳定后：

```text
FROZEN
```

---

# 8. Run / Experience Lifecycle

实时：

```text
Trace Event
```

任务结束：

```text
Run Sealed
```

之后：

```text
Experience Extraction
```

跨多个 Run：

```text
Pattern Detection
```

再触发：

```text
Evolution
```

粒度：

```text
Event = Observability Unit
Run = Experience Unit
Window = Evolution Unit
```

---

# 9. Evolution Architecture

```text
Execution
 ↓
Evaluation
 ↓
Structured Experience
 ↓
Signal Detection
 ↓
Failure Attribution
 ↓
Evolution Proposal
 ↓
Candidate Strategy
 ↓
Validation Gate
 ↓
Promote / Reject
```

---

# 10. V1 Mutation Operators

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
SEQUENTIAL_TO_PARALLEL
PARALLEL_TO_SEQUENTIAL
MAKE_CONDITIONAL
CHANGE_RETRY_POLICY
CHANGE_REPLAN_POLICY
```

暂不允许：

```text
CREATE_ARBITRARY_ROLE
FREEFORM_CODE_WORKFLOW
UNBOUNDED_LOOP
EVOLUTION_ENGINE_SELF_MODIFICATION
OPEN_ENDED_CROSSOVER
```

---

# 11. Failure Attribution

Candidate Attribution Target：

```text
Agent
Prompt
Skill
Tool
Edge
Topology
Execution Policy
```

Evidence：

```text
Rule
Trace
Evaluator
LLM Attribution
```

建议结构：

```json
{
  "failure_tag": "numeric_error",
  "target_type": "role",
  "target_id": "analyst",
  "evidence": [],
  "confidence": 0.82
}
```

---

# 12. Validation Gate

原则：

> Candidate 与 Current Strategy 在同一验证任务集上考试。

第一版 Promotion Policy：

```text
Hard Quality Constraint
+
Minimum Improvement
+
Cost Guardrail
+
Latency Guardrail
```

具体阈值后续实验确定。

---

# 13. Complexity Control

必须记录：

```text
Agent Count
Edge Count
Communication Round
Token
Tool Call
Retry
Latency
```

Evolution 同时支持：

```text
Growth
+
Pruning
```

---

# 14. Three Benchmark Domains

## Report Generation

用于研究：

```text
Search
Writer
Fact Check
Citation
```

## Data Analysis

用于研究：

```text
Analyst
Python
Numeric Verification
```

## Task Planning

用于研究：

```text
Planning
Constraint
Risk
Resource
```

它们当前是 Benchmark Domains，而不是三个产品。

---

# 15. Relationship with openJiuwen

使用：

```text
openJiuwen Core
```

作为：

```text
Agent Runtime Primitive
```

第一阶段不以 Agent Studio 或 JiuwenSwarm 作为项目主体。

JiuwenSwarm 作为：

```text
Reference Implementation / Baseline / Optional Integration
```

---

# 16. Product UI Hypothesis

不是 Chat UI 优先。

核心页面：

```text
Task Workspace
Strategy Library
Team Graph
Execution Timeline
Evaluation Dashboard
Evolution Diff
Generation History
```

---

# 17. Core Innovation Candidates

## I1

Task-Adaptive Team Formation

## I2

Experience-Driven Strategy Evolution

## I3

Validation-Gated Reversible Evolution

## I4 — Product Differentiator

Evolution Governance

包括：

```text
Version
Evidence
Candidate
Validation
Promotion
Rollback
Freeze
```

---

# 18. V1 Non-Goals

暂不做：

```text
通用任意领域承诺
无限 Role Creation
开放式 RSI
模型权重训练
生产级分布式 Swarm
复杂账号系统
插件市场
```

---

# 19. Open Questions Before Freeze

## O1 Strategy Branching

- 分支创建阈值；
- Parent / Child 继承；
- Generalization to Parent；
- Branch Merge 是否需要 V1 支持。

## O2 Failure Attribution

- LLM Attribution 可靠性；
- Reviewer / Verifier / Evaluator 的边界；
- 如何处理多因素失败。

## O3 Mutation Search

- 一次生成多少 Candidate；
- 是否需要 Beam / MCTS；
- Search Budget。

## O4 Validation

- 数据集划分；
- LLM Judge 稳定性；
- 随机性和重复实验次数。

## O5 Initial Formation

- Task Analyzer 是规则还是 LLM；
- Strategy Retrieval 优先级；
- 无匹配 Strategy 时怎么办。

---

# 20. Current Working Thesis

> **EvoTeam 不让 Agent Team 在每次任务中简单重试，而让跨任务经验改变下一次团队如何被组织。**

> **Memory 记录过去，Evolution 改变未来。**

> **好的自演进系统不仅要会改变，还必须知道什么时候不应该改变。**
