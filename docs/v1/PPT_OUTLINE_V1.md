# EvoTeam PPT Outline V1

> 用途：阶段汇报 / 项目答辩 PPT 制作蓝本  
> 项目：EvoTeam —— 基于 openJiuwen 的经验驱动自演进多智能体组织系统

## 核心叙事

整套 PPT 按以下逻辑展开：

```text
问题 → 洞察 → 核心抽象 → 自演进机制 → 系统架构 → 验证方法 → 项目计划
```

核心句：

> **我们不是只构建一支 Agent Team，而是让这支 Team 根据经验学会如何重新组织自己。**

三个核心原则：

> **任务决定初始组织。**  
> **证据决定问题归因。**  
> **验证决定组织是否换代。**

---

## Slide 1｜封面

**EvoTeam**

副标题：

> 基于 openJiuwen 的经验驱动自演进多智能体组织系统

英文 Tagline：

> Build a team that learns how to organize itself.

页面元素：项目名称、赛题名称、团队成员、学校/学院、日期。

---

## Slide 2｜背景：为什么需要 Multi-Agent

复杂任务往往同时需要：

```text
理解 / 规划 / 检索 / 分析 / 执行 / 写作 / 验证
```

单 Agent 的局限：

- 职责混杂；
- 上下文负担重；
- 错误难独立验证；
- 不同能力难形成专业化协作。

核心结论：

> 多 Agent 的价值不在“数量更多”，而在“形成可组织的职责协作”。

---

## Slide 3｜现有 Multi-Agent 的痛点

典型固定结构：

```text
Planner → Executor → Critic
```

不同任务仍使用相同 Team：

```text
Task 1 → Same Team
Task 2 → Same Team
Task 3 → Same Team
```

问题：

- 角色固定；
- Agent 数量固定；
- 通信路径固定；
- Prompt 依赖人工；
- 历史经验难以影响未来任务；
- Agent 越多不一定越好。

核心问题：

> 为什么 Agent Team 每接一个新项目，都像一支没有组织记忆的临时团队？

---

## Slide 4｜赛题理解

赛题要求：

```text
3+ Agent
协作机制
自演进
Before vs After
3 类任务
可解释 / 可复现
```

重点突出：

# Self-Evolution

结论：

> Multi-Agent 是基础，自演进才是区分度。

---

## Slide 5｜Retry ≠ Evolution

Retry：

```text
Task → Fail → Reflect → Retry → End
```

特点：

- 任务内；
- 临时；
- 不形成长期版本；
- 不一定影响未来。

Evolution：

```text
多次 Task
→ Experience
→ Failure Pattern
→ Strategy Mutation
→ Validation
→ Future Task
```

核心句：

> Memory 记录过去，Evolution 改变未来。

---

## Slide 6｜公司类比

| 现实组织 | EvoTeam |
| --- | --- |
| 项目 | Task |
| 员工 | Agent |
| 岗位 | Role |
| 专业能力 | Skill |
| 工作工具 | Tool |
| 项目组 | Team |
| 工作制度 | Strategy |
| 绩效评估 | Evaluation |
| 组织经验 | Experience |
| 组织调整 | Evolution |

案例：

```text
连续数字错误 → 增加验证能力
低贡献岗位 → 删除 / 条件调用
```

---

## Slide 7｜EvoTeam 产品定位

EvoTeam 是 openJiuwen Core 之上的：

> **Agent Organization Evolution Layer**

openJiuwen Core 负责：

- Agent Runtime
- Model
- Tool
- Workflow / ReAct 基础能力

EvoTeam 负责：

- Task Analysis
- Strategy Library
- Dynamic Team Formation
- Orchestration
- Evaluation
- Experience
- Failure Attribution
- Mutation
- Validation
- Promotion / Rollback

---

## Slide 8｜核心抽象：Strategy

```text
Strategy =
Role
+ Skill
+ Tool
+ Prompt
+ Team Topology
+ Execution Policy
```

演进表达为：

```text
Strategy v1 → v2 → v3
```

每个版本支持：

- Diff
- Compare
- Validate
- Promote
- Rollback
- Freeze

核心句：

> Strategy 是 EvoTeam 的核心演进单元。

---

## Slide 9｜任务决定初始组织

```text
Task
↓
Task Analyzer
↓
Task Signature
↓
Strategy Router
↓
Role / Skill / Tool Selection
↓
Team
```

示例：

- Report：Planner / Researcher / Writer / Verifier
- Data：Planner / Analyst / Verifier / Critic
- Planning：Planner / Analyst / Verifier / Critic

强调：

> Task Family 不是“大 Agent 类型”。

---

## Slide 10｜Strategy Family

```text
              BaseReport
            /     |      \
       General   News   Academic
```

News Delta：

```text
+ web-search
+ freshness-check
+ timeline-check
```

Academic Delta：

```text
+ paper-search
+ citation-check
+ academic-writing
```

机制：

```text
Parent → Child = Specialization
Child → Parent = Generalization
```

---

## Slide 11｜Experience 三层粒度

```text
Trace Event
↓
Sealed Run
↓
Evolution Window
```

含义：

```text
Event = Observe
Run   = Learn
Window= Evolve
```

核心句：

> EvoTeam 不会因为一句错误就立刻改变自己，而是在跨任务证据达到条件后才触发演进。

---

## Slide 12｜Evidence-Based Failure Attribution

最终错误可能来自：

```text
Analyst
Tool
Verifier
Planner
Topology
```

机制：

```text
Deterministic Evidence
+
Trace Provenance
+
LLM Attribution
↓
Failure Attribution
```

输出：

- Origin Failure
- Control Failure
- Confidence
- Mutation Scope

---

## Slide 13｜Mutation Search

同一个失败生成 2–3 个 Candidate：

```text
A：Prompt Update
B：Tool Policy
C：Add Verifier
```

原则：

- Typed Mutation
- Minimal Mutation
- Schema-Constrained
- 不直接修改线上 Strategy

---

## Slide 14｜Validation Gate

```text
Current Strategy ─────┐
                      ├→ Held-out Validation Set
Candidate Strategy ───┘
                      ↓
          Quality / Cost / Latency
              / Complexity
                      ↓
              Promote / Reject
```

核心解释：

> 新旧 Strategy 做同一套考试，只有收益足够大且代价可接受才换代。

---

## Slide 15｜Growth + Pruning

Evolution Candidate 可以：

```text
+ Agent
- Agent
+ Edge
- Edge
Conditional Agent
Sequential ↔ Parallel
```

核心句：

> Evolution ≠ More Agents  
> Evolution = Better Organization

---

## Slide 16｜完整闭环

```text
Task
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
Attribution
↓
Mutation
↓
Validation
↓
Next Generation
```

旁边固定：

> 任务决定初始组织。  
> 证据决定问题归因。  
> 验证决定组织是否换代。

---

## Slide 17｜系统架构

四层：

```text
Evolution Console
↓
EvoTeam Core
↓
Runtime Adapter
↓
openJiuwen Core
```

EvoTeam Core：

```text
Task Analyzer
Strategy Library
Team Orchestrator
Evaluator
Experience Store
Attribution
Mutation Planner
Validation Gate
```

---

## Slide 18｜Related Work 与项目位置

方向：

- Reflection / Memory
- Dynamic Team
- Communication Graph Optimization
- Agent System Search
- Multi-Agent Self-Evolution

代表工作：

- Reflexion
- Voyager
- DyLAN
- GPTSwarm
- AgentPrune
- ADAS / AFlow
- EvoMAS
- Meta-Team
- JiuwenSwarm

落点：

> EvoTeam 聚焦可治理、可版本化、可验证的组织级 Strategy Evolution。

关键词：

# Evolution Governance

---

## Slide 19｜实验设计

Baselines：

```text
Single Agent
Fixed Multi-Agent
Fixed Multi-Agent + Retry
Dynamic Team
EvoTeam
```

三类 Benchmark：

```text
Report
Data
Planning
```

指标：

```text
Quality
Success Rate
Token
Cost
Latency
Agent Count
Edge Count
Retry
```

---

## Slide 20｜项目计划

当前：

```text
产品定义 ✅
Strategy 机制 ✅
架构设计 ✅
实验设计 ✅
Related Work ✅
```

下一阶段：

```text
openJiuwen Core 验证
→ EvoTeam Core
→ Multi-Agent Baseline
→ Evaluation / Trace
→ Evolution v1
→ Team Evolution
→ Visualization
→ Benchmark Experiments
```

---

## Slide 21｜结束页

> **We do not only build an Agent Team.  
> We build a Team that learns how to organize itself.**

中文：

> **我们不是只构建一支 Agent Team，而是让这支 Team 学会如何重新组织自己。**

---

## 正式制图优先级

优先精修 5 张图：

1. EvoTeam / openJiuwen 边界图
2. Strategy Family 图
3. Event / Run / Window 图
4. Failure Attribution 图
5. Mutation + Validation Gate 图
