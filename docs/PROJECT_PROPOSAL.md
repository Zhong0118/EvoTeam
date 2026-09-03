# EvoTeam 项目申请书

> 项目名称：EvoTeam —— 基于 openJiuwen 的经验驱动自演进多智能体组织系统  
> 文档状态：项目申请 / 报名材料 V1  
> 说明：采用通用项目申请书结构，可根据比赛报名系统字段进一步拆分。

## 一、项目简介

随着大语言模型 Agent 能力快速发展，单一 Agent 已逐渐从问答工具扩展到任务规划、信息检索、数据分析、代码执行和报告生成等复杂场景。面对需要多种能力协同完成的复杂任务，多智能体系统能够通过角色分工和协作机制提高任务完成能力。

然而，当前多智能体系统普遍依赖人工预先设计的固定角色、固定 Agent 数量和固定工作流。即使系统能够在单次任务中通过 Critic、Reflection 或 Retry 机制进行纠错，这些调整通常只作用于当前任务，历史经验难以稳定转化为影响未来任务的组织策略。

EvoTeam 希望研究：

> **Agent Team 是否能够像真实组织一样，根据任务需求和跨任务历史经验，持续调整自身的角色组合、能力配置、通信路径与执行策略。**

项目基于 openJiuwen Core 构建底层 Agent Runtime，在此基础上设计 Task Analyzer、Strategy Library、Team Orchestrator、Evaluator、Experience Store、Failure Attribution、Mutation Planner 与 Validation Gate，形成：

```text
任务理解
→ 动态组队
→ 多智能体协作
→ 任务评价
→ 经验沉淀
→ 失败归因
→ Strategy 变异
→ 候选验证
→ 晋升 / 回滚
```

完整闭环。

---

## 二、项目背景与问题分析

### 1. 为什么需要 Multi-Agent

复杂任务往往同时需要：

```text
理解
规划
检索
分析
执行
写作
验证
```

多个职责。单 Agent 同时承担所有能力容易造成职责混杂、上下文负担过重和错误缺乏独立校验，因此多智能体协作成为 Agent 系统的重要方向。

### 2. 现有多智能体系统局限

#### 组织结构固定

常见：

```text
Planner → Executor → Critic
```

不同任务仍使用相同 Team。

#### 协作策略依赖人工设计

Role、Prompt、Tool 与通信路径通常需要人工固定。

#### Memory 不等于 Evolution

系统即使记住历史，也未必会因此改变未来的组织 Strategy。

#### Self-Reflection 多停留在任务内部

```text
Fail → Reflect → Retry
```

不等于跨任务的长期演进。

#### Multi-Agent 成本高

增加 Agent 会增加 Token、Latency、API Cost 与 Communication Complexity。

因此：

> **更多 Agent 并不必然意味着更好的系统。**

---

## 三、项目目标

### 目标 1：Task-Adaptive Team Formation

根据 Task Signature 自动：

- 识别任务类型；
- 判断能力需求；
- 选择 Role；
- 配置 Skill；
- 配置 Tool；
- 形成初始 Team Topology。

### 目标 2：跨任务经验沉淀

记录：

```text
Task
Strategy
Team
Trace
Tool Calls
Evaluation
Failure Tags
Token
Cost
Latency
Outcome
```

形成可供未来演进使用的结构化经验。

### 目标 3：Evidence-Based Failure Attribution

任务失败后判断真正应该修改：

```text
Agent
Prompt
Skill
Tool
Edge
Topology
Execution Policy
```

归因依据：

```text
Deterministic Evidence
+
Trace Provenance
+
LLM Attribution
```

### 目标 4：Strategy Evolution

根据归因结果产生受约束 Mutation：

- Prompt Update
- Skill Add / Remove
- Tool Add / Remove
- Add / Remove Existing Role
- Add / Remove Edge
- Sequential / Parallel
- Conditional Agent
- Retry / Replan Policy

### 目标 5：Validation-Gated Evolution

Candidate Strategy 必须经过：

```text
Static Validation
→ Smoke Test
→ Mini Validation
→ Full Validation
```

只有通过验证才 Promote，否则 Reject / Rollback。

---

## 四、核心设计思想

三个核心原则：

> **任务决定初始组织。**

> **证据决定问题归因。**

> **验证决定组织是否换代。**

辅助原则：

> **Memory 记录过去，Evolution 改变未来。**

---

## 五、核心抽象

### Role

V1 固定基础 Role Pool：

- Planner / Coordinator
- Researcher
- Analyst / Executor
- Writer / Synthesizer
- Verifier
- Critic / Reviewer

### Skill

表示 Agent 可复用的专业能力。

例如：

- Web Research
- Paper Search
- Statistical Analysis
- Citation Verification
- Timeline Analysis

### Tool

例如：

- Web Search
- Python
- Database
- Calculator
- File Reader

### Strategy

Strategy 是核心演进单元，包含：

```text
Role Composition
Skill Configuration
Tool Policy
Prompt Policy
Communication Topology
Execution Policy
Retry / Replan Policy
```

---

## 六、Strategy Family

EvoTeam 不使用一个全局万能 Strategy，也不为每个任务创建永久 Strategy。

采用：

```text
Strategy Family
+
Specialized Variant
```

例如：

```text
Report
├── General
├── News
└── Academic
```

子 Variant 采用：

```text
Parent Base
+
Variant Delta
```

而不是完整复制父 Strategy。

首次出现的新需求先形成临时 Variant，只有同类需求持续出现并验证有效后，才升级为 Persistent Variant。

同时支持：

```text
Specialization
```

与：

```text
Generalization
```

如果子 Variant 中的能力在多个兄弟任务上同样有效，则提升回 Parent Strategy。

---

## 七、经验存储机制

### Event

实时记录 Agent、Tool、Message、Evaluation 等 Trace。

### Run

Task 完成、失败、取消或超时后：

```text
Run → SEALED
```

Run 是主要学习单位。

### Evolution Window

聚合多个同类 Run，用于检测：

- Repeated Failure
- Performance Drift
- Low Contribution
- High Cost
- Tool Failure Pattern

因此：

```text
Event = Observe
Run = Learn
Window = Evolve
```

---

## 八、Failure Attribution

一次失败可能由多个因素共同造成，例如：

```text
Analyst 产生错误
+
Verifier 未发现错误
```

因此区分：

- Origin Failure
- Control Failure

采用：

```text
Rule
+
Trace / Provenance
+
LLM Attribution
```

联合归因。

---

## 九、Mutation Search

V1 采用：

> **Schema-Constrained Typed Mutation**

不允许 LLM 自由重写整个系统。

一次 Evolution Event 推荐生成 2–3 个 Candidate。

每个 Candidate 尽量 Minimal Mutation，只修改一个核心因素，以提高：

- 可解释性；
- 可复现性；
- 消融能力；
- 回滚能力。

---

## 十、Validation Gate

Candidate 不直接上线。

```text
Current Strategy ─┐
                  ├→ Same Held-out Validation Set
Candidate ────────┘
                  ↓
         Metrics Comparison
```

### Quality

- Task Success
- Accuracy
- Completeness
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

系统同时支持：

### Quality-Oriented Evolution

质量明显提升，成本可接受。

### Efficiency-Oriented Evolution

质量基本保持，但成本、延迟或复杂度明显下降。

---

## 十一、Organization Pruning

Evolution 不只增加 Agent，还允许：

```text
Remove Agent
Remove Edge
Conditional Agent
Reduce Communication
```

核心：

> **Evolution ≠ More Agents. Evolution = Better Organization.**

---

## 十二、系统架构

### Layer 1：Evolution Console

展示：

- Task
- Strategy
- Team Graph
- Trace
- Evaluation
- Evolution Diff
- Generation History

### Layer 2：EvoTeam Core

包含：

```text
Task Analyzer
Strategy Library
Strategy Router
Team Orchestrator
Evaluator
Experience Store
Signal Detector
Failure Attribution
Mutation Planner
Candidate Pool
Validation Gate
Strategy Registry
```

### Layer 3：Runtime Abstraction

隔离具体 Agent Framework。

### Layer 4：openJiuwen Core

负责：

- Agent
- Model
- Tool
- Workflow
- Runtime

---

## 十三、自演进闭环

```text
Task
↓
Task Analyzer
↓
Strategy
↓
Team
↓
Run
↓
Evaluation
↓
Experience
↓
Failure Attribution
↓
Mutation Search
↓
Candidate Strategy
↓
Validation
↓
Promote / Reject
↓
Next Generation
```

---

## 十四、创新点

### 1. Task-Adaptive Team Formation

根据 Task Signature 动态形成 Team。

### 2. Experience-Driven Strategy Evolution

让跨任务经验改变未来 Strategy。

### 3. Evidence-Based Failure Attribution

使用确定性证据、Trace 与 LLM 联合归因。

### 4. Validation-Gated Reversible Evolution

Candidate 必须通过独立验证才能换代，并支持 Rollback / Freeze。

### 5. Complexity-Aware Organization Evolution

同时支持 Growth 和 Pruning。

### 6. Evolution Governance

系统记录：

```text
为什么变
证据是什么
改了什么
有哪些 Candidate
验证结果
为什么 Promote / Reject
能否 Rollback
何时 Freeze
```

使自演进过程具备可解释、可验证、可治理特征。

---

## 十五、与 openJiuwen 的关系

openJiuwen Core 提供：

```text
Agent Runtime
Model
Tool
Workflow / ReAct Primitive
```

EvoTeam 在其上实现：

```text
Organization
Strategy
Evaluation
Experience
Attribution
Evolution
Validation
Governance
```

第一阶段不以 Agent Studio 或 JiuwenSwarm 作为项目主体。

---

## 十六、与 RSI 的关系

EvoTeam V1 不宣称实现完整 Recursive Self-Improvement。

因为：

```text
Evolution Engine
Mutation Operator
Validation Policy
```

仍由开发者约束。

当前定位：

> **Controlled / Bounded Inter-task Self-Evolution**

Future Work 可研究：

- Mutation Policy Evolution
- Evaluator Evolution
- Search Policy Evolution
- Evolution Trigger Evolution

---

## 十七、实验设计

三类 Benchmark：

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

---

## 十八、Baseline

```text
Single Agent
Fixed Multi-Agent
Fixed Multi-Agent + Retry
Dynamic Team
EvoTeam
```

用于回答：

1. Multi-Agent 是否真正有效？
2. Dynamic Team 是否优于 Fixed Team？
3. Retry 是否可以替代 Evolution？
4. Cross-task Evolution 是否产生额外收益？

---

## 十九、消融实验

移除或关闭：

- Dynamic Team
- Experience
- Attribution
- Prompt / Tool Evolution
- Team Evolution
- Validation Gate

观察各机制贡献。

---

## 二十、评价指标

### Performance

- Quality
- Success Rate
- Error Rate

### Efficiency

- Token
- API Cost
- Latency
- Tool Calls

### Organization Complexity

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

---

## 二十一、预期成果

1. EvoTeam 系统原型；
2. openJiuwen Runtime Adapter；
3. Strategy Library；
4. Dynamic Team Formation；
5. Failure Attribution Engine；
6. Strategy Evolution Engine；
7. Validation Gate；
8. Evolution Console；
9. 三类 Benchmark；
10. 可复现实验脚本；
11. Before / After 演进案例；
12. 技术文档；
13. 汇报 PPT；
14. 演示视频。

---

## 二十二、实施计划

### Phase 1：产品与研究设计

- 赛题分析
- Product Spec
- Related Work
- Architecture
- Experiment Design

### Phase 2：openJiuwen Core 验证

- Agent
- Tool
- Structured Output
- Async / Streaming
- ReAct / Workflow

### Phase 3：EvoTeam Core

- Domain Model
- Runtime Protocol
- Strategy
- Task Analyzer
- Trace

### Phase 4：Multi-Agent Baseline

- Planner
- Executor / Analyst
- Critic / Verifier
- Orchestrator

### Phase 5：Evaluation / Experience

- Evaluator
- Trace Store
- Run Store
- Failure Tags

### Phase 6：Evolution V1

- Trigger
- Attribution
- Typed Mutation
- Candidate
- Validation
- Promotion / Rollback

### Phase 7：Team Evolution

- Add / Remove Agent
- Add / Remove Edge
- Conditional
- Parallel / Sequential
- Pruning

### Phase 8：Visualization & Experiments

- Team Graph
- Timeline
- Evolution Diff
- Generation History
- Benchmark
- Ablation

---

## 二十三、团队协作

项目由 3 名成员协作完成。

建议按阶段和模块分工，而不是一人一个永久分支。

后续可考虑：

- 核心系统 / Evolution Engine
- openJiuwen Integration / Backend
- Evaluation / Frontend / Experiments

最终分工根据成员实际能力确定。

---

## 二十四、风险与应对

### Search Space 过大

应对：

- 固定 Role Pool
- Typed Mutation
- Minimal Mutation
- Candidate 数量限制

### Attribution 不稳定

应对：

- Rule
- Trace
- LLM 联合
- Confidence
- 后续 Counterfactual Replay

### Evolution Cost 过高

应对：

```text
Static → Smoke → Mini → Full
```

### Agent 越演进越多

应对：

- Complexity Metrics
- Agent Pruning
- Edge Pruning
- Conditional Agent
- Freeze

### 过拟合历史任务

应对：

```text
History Set
Validation Set
Test Set
```

严格分离。

---

## 二十五、项目特色总结

EvoTeam 的核心不是：

```text
“实现很多 Agent”
```

而是：

> **把 Multi-Agent 从一次性的协作流程，转化为一个能够积累组织经验、进行问题归因、产生候选策略、接受验证并完成组织换代的持续演进系统。**

最终希望证明：

> **Agent Team 不仅可以完成任务，还可以逐渐学习下一次应该如何组织自己。**
