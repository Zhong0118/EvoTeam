# EvoTeam 产品讨论纪要：2026-09-03

> 状态：讨论收敛中，尚未完全冻结  
> 目的：记录本轮围绕 EvoTeam 产品思想、自演进机制、Strategy、Memory、验证与多智能体协作的关键结论。

---

# 1. 当前项目核心定位

当前推荐定义：

> **EvoTeam 是一个基于 openJiuwen Core 的经验驱动多智能体组织演进系统。**

它不以“做更多 Agent”为目标，而是研究：

> **一支 Agent Team 如何根据跨任务执行经验，改变未来的组织结构、协作路径、Prompt、Skill 与 Tool 使用策略。**

当前核心演进对象不定义为单个 Agent，而定义为：

```text
Strategy
```

Strategy 包含：

```text
Agent Roles
Team Topology
Prompts
Skills
Tool Policies
Routing / Execution Policy
```

---

# 2. 关于 RSI：EvoTeam 像，但 V1 不是严格 RSI

RSI 通常指 Recursive Self-Improvement（递归自我改进）。

严格意义上的 RSI 不只是：

```text
系统改进自己的任务策略
```

而是：

```text
系统改进“用于改进自己的机制”
        ↓
新的改进机制继续改进系统
        ↓
甚至继续改进下一代改进机制
```

EvoTeam V1 当前设计更接近：

```text
Bounded / Controlled Self-Evolution
```

因为以下部分仍由开发者固定：

- Evolution Engine；
- Mutation Operator 集合；
- Evaluator；
- Validation Gate；
- Promotion Policy；
- Search Space。

EvoTeam V1：

```text
固定的 Evolution Engine
        ↓
优化 Strategy
```

如果未来演进到：

```text
Evolution Engine v1
        ↓
优化 Mutation Policy
        ↓
Evolution Engine v2
        ↓
再优化自己的搜索和评价方法
```

那么会更接近“受控的 Recursive Self-Improvement”。

因此当前建议：

> 不在比赛主叙事中直接宣称 EvoTeam 是 RSI 系统。

可以说：

> EvoTeam 与 RSI 共享“系统利用自身运行结果持续改进未来行为”的思想，但 V1 采用有边界、可验证、可回滚的组织级自演进，而不是开放式递归自修改。

---

# 3. Q1：Strategy 应采用分支式演进，而不是单线无限演进

当前结论：

```text
选择：Strategy Family + Specialized Variant
```

示例：

```text
ReportStrategy
│
├── GeneralReport
├── NewsReport
├── AcademicReport
├── DisasterReport
└── MedicalReport
```

但是不建议完全照搬 Git Branch。

更准确的模型是：

```text
Base Strategy
    +
Specialized Delta
```

例如：

```text
BaseReportStrategy
├── Planner
├── Researcher
├── Writer
└── Verifier
```

AcademicReport 只覆盖：

```text
+ Literature Search Skill
+ Citation Verification
+ Academic Writer Prompt
```

NewsReport 覆盖：

```text
+ Freshness Check
+ Web Search
+ Timeline Verification
```

## 什么时候分支？

不是“一看到新关键词就创建分支”。

建议满足以下条件之一：

1. 当前任务与已有 Strategy 的 capability profile 显著不同；
2. 同一类特殊需求重复出现；
3. 现有 Strategy 在该子分布上持续失败；
4. 专用 Candidate Strategy 在该子分布验证集上明显优于父 Strategy。

这样可以避免：

```text
每个任务一个 Strategy
```

导致 Strategy Explosion。

## 怎么“合并”？

不建议第一版做 Git 式双向 merge。

建议做：

### Promotion to Parent

如果某个子分支上的改进：

```text
AcademicReport:
新增 Source Reliability Check
```

在：

```text
NewsReport
DisasterReport
GeneralReport
```

上也被验证有效，那么将该能力提升为：

```text
BaseReportStrategy
```

因此：

```text
分支 = 特化
向上推广 = 泛化
```

## Freeze

如果：

- 连续若干 Candidate 无显著提升；
- 最近若干代提升小于阈值；
- Evolution Budget 达到上限；

则：

```text
Strategy → FROZEN
```

新 Failure Pattern 出现后再解冻。

---

# 4. Q2：固定 Role Archetype，动态演进 Skill / Tool / Strategy

当前结论：

```text
选择：固定基础 Role Pool + 动态能力组合
```

V1 推荐基础 Role：

| Role | 作用 |
| --- | --- |
| Planner / Coordinator | 理解任务、拆解、制定计划 |
| Researcher | 检索、资料收集 |
| Analyst / Executor | 推理、计算、任务执行 |
| Writer / Synthesizer | 汇总、组织最终输出 |
| Verifier | 数值、事实、约束校验 |
| Critic / Reviewer | 整体质量审查 |

关键概念必须区分：

```text
Role  = 你是谁
Skill = 你会什么
Tool  = 你能调用什么
Strategy = 谁参与，以及怎么协作
```

例如：

```text
Researcher
├── Skill: web-research
├── Skill: paper-research
└── Tool: Search API
```

而不是：

```text
WebSearchAgent
PaperSearchAgent
NewsSearchAgent
...
```

V1 暂不允许 LLM 无限创造新 Role。

---

# 5. Q3：第一次任务采用 Task Analyzer + Role Pool 动态组队

当前推荐：

```text
Task
 ↓
Task Analyzer
 ↓
Task Profile
 ↓
Capability Requirements
 ↓
Role / Skill / Tool Selection
 ↓
Initial Team Strategy
```

示例：

```json
{
  "task_family": "report",
  "needs_search": true,
  "needs_calculation": false,
  "needs_writing": true,
  "needs_fact_check": true,
  "freshness_sensitive": true
}
```

初始 Team：

```text
Planner
Researcher
Writer
Verifier
```

所以：

> 动态组队不是必须先有历史经验才能发生。

第一次任务依靠 Task Profile。

之后：

> 历史经验负责让同类任务下一次组得更好。

---

# 6. Q4：Strategy 按 Task Family 管理，并允许子分支

当前推荐：

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

不采用一个 Global Strategy 管全部任务，也不采用每个任务一个永久 Strategy。

---

# 7. Q5：Evolution Mutation 使用 Rule + LLM + Search / Validation

当前推荐三层：

```text
Signal Detection
     ↓
Diagnosis / Attribution
     ↓
Mutation Search
```

Rule 负责稳定检测失败、反馈、成本和性能异常；LLM 负责解释“为什么”和“应该改哪里”；Search 在 V1 中保持轻量，先让 LLM 生成 2~3 个 Candidate，再交给 Validation Ranking。

后期才考虑 Beam Search、MCTS、Evolutionary Search 或 Bandit。

---

# 8. Q6：Experience 不等于 Conversation Memory

这是当前非常重要的决定。

建议使用三种不同粒度：

## 8.1 Event 粒度：实时记录

每个重要步骤实时 append：

```text
AGENT_STARTED
AGENT_COMPLETED
TOOL_CALLED
TOOL_RESULT
MESSAGE_TRANSFER
EVALUATION
```

用途：可观察、Debug、Trace、后续归因。

## 8.2 Run / Task 粒度：任务结束时封存

一个任务完成、失败、取消或超时后：

```text
Run → SEALED
```

形成 Task Summary：

```json
{
  "task": {},
  "strategy": {},
  "agents": [],
  "trace_summary": {},
  "quality": 0.0,
  "cost": 0.0,
  "latency": 0.0,
  "token_usage": {},
  "failure_tags": [],
  "outcome": ""
}
```

这是最重要的学习单元。

## 8.3 Evolution Window：跨任务聚合

例如：

```text
最近 10 个同 Family Run
```

或者直到某 Failure Tag 累计超过阈值，再做 Pattern Mining。

所以：

```text
Event = 观察单位
Task / Run = 经验单位
Window = 演进判断单位
```

## Session 和 Task 必须区分

一个 Session 里可能包含多个 Task，因此不能把“会话结束”等同于“任务结束”。

Task 建议状态：

```text
CREATED
RUNNING
SUCCEEDED
FAILED
CANCELLED
TIMEOUT
SEALED
```

SEALED 后才进入 Experience Aggregation。

---

# 9. Q7：Evolution 由触发条件启动，并存在 Plateau / Freeze

推荐 Trigger：

```text
Repeated Failure
Performance Drift
Negative Feedback
High Cost
High Latency
Low Agent Contribution
Tool Failure Pattern
```

推荐限制：

```text
Cooldown
Max Candidate Count
Evolution Budget
Max Generations
Plateau Detection
```

---

# 10. Q8：Validation Gate 的大白话解释

假设当前是：

```text
DataStrategy v3
```

最近 10 个任务里 4 个数字算错，于是提出：

```text
Candidate v4:
加入 Verifier
```

不能只把刚才失败的 4 个任务重跑一遍就说成功。

应该准备一组没有直接参与“发现问题”的 Validation Tasks，例如 20 个数据分析任务。

然后：

```text
v3 跑同样 20 个任务
v4 跑同样 20 个任务
```

比如得到：

```text
                v3       v4
Quality         82       88
Numeric Error   15%      4%
Cost            1.00     1.08
Latency         1.00     1.12
```

质量明显提升、成本和延迟可接受：

```text
v4 → PROMOTE
```

如果：

```text
Quality 82 → 83
Cost 1.00 → 1.80
```

则：

```text
v4 → REJECT
```

一句话：

> **新旧方案做同一套考试，只有收益足够大且代价可接受才换代。**

V1 推荐使用：

```text
Hard Constraints
+
Minimum Quality Improvement
+
Cost Guardrail
+
Latency Guardrail
```

而不是只用一个难解释的综合 Reward。

---

# 11. Q9：任务驱动 vs 功能驱动

当前推荐：

# Task-Driven Team, Role-Based Agents

即：

```text
任务驱动组队
+
功能角色作为基本协作单位
```

不建议：

```text
NewsReportAgent
AcademicReportAgent
DataAnalysisAgent
PlanningAgent
```

这些“大 Agent”内部再藏子 Agent。

正确理解：

```text
Task
 ↓
Strategy Selection / Formation
 ↓
Team
 ├── Planner
 ├── Researcher
 ├── Analyst
 ├── Writer
 └── Verifier
```

News Report 是 Task Family / Strategy Variant，不是 Agent 类型。

对“路径性能”的理解基本正确：

```text
Planner → Executor → Critic
```

和：

```text
Planner → Executor → Critic → Replan → Executor
```

确实是不同的 Team Topology / Execution Policy。

但 V1 不允许任意排列节点，而是受 Schema 约束地做 Graph Transformation。

允许：

```text
Add Verification Step
Remove Low-value Step
Add Feedback Edge
Sequential ↔ Parallel
Conditional Branch
Retry / Replan Policy
```

不允许：

```text
无限循环
任意重复节点
无约束完全图
```

---

# 12. Verifier、Evaluator、Attribution Agent 的边界

## Verifier Agent

属于任务团队。

回答：

> 当前结果有没有具体错误？

## Evaluator

属于系统评价层。

回答：

> 整个 Team Strategy 表现好不好？

Evaluator 不一定是 Agent，可以是 Rule、Ground Truth、LLM Judge、Unit Test 和 Metric Calculator 的组合。

## Attribution Agent

可以单独存在。

回答：

> 如果失败，究竟该怪哪里？

候选目标：

```text
Agent
Prompt
Skill
Tool
Edge
Topology
Execution Policy
```

V1 不应完全相信 Attribution Agent，而应结合 Rule Evidence、Trace Evidence 和 LLM Attribution。

---

# 13. Q10：必须同时支持 Growth 和 Pruning

Evolution Mutation：

```text
ADD
REMOVE
REPLACE
REWIRE
CONDITIONALIZE
```

都应该存在。

目标不是更多 Agent，而是更合适的组织。

---

# 14. Q11：与 JiuwenSwarm 的边界

JiuwenSwarm 已经具有 Leader / Teammate、多 Agent 协作、Task Memory、Skill Self-Evolution、Reviewer Feedback Attribution、evolutions.json、SwarmFlow 等能力。

因此 EvoTeam 不能将“多 Agent”“Task Memory”“失败后改 Skill”单独作为主要创新。

当前推荐差异：

```text
JiuwenSwarm
  └── Agent / Skill 如何越用越强

EvoTeam
  └── Team Strategy 如何跨任务被版本化、比较、变异、验证、晋升、回滚
```

重点：

```text
Team Topology Evolution
Strategy Family
Validation Gate
Promotion / Rollback
Organization Pruning
Cross-task Benchmark
```

---

# 15. Q12：当前产品形态

当前推荐：

> **Self-Evolving Agent Organization Lab / Platform**

核心用户：

```text
Agent Developer
Researcher
AI Application Team
```

核心产品对象：

```text
Task
Strategy
Team
Run
Trace
Evaluation
Experience
Evolution
Generation
```

报告生成、数据分析、任务规划更适合作为 Benchmark Domains，而不是三个彼此独立的产品。

---

# 16. 当前仍需重点讨论的三件事

## O1：Strategy Branch / Generalization

需要继续确定：

- 分支阈值；
- Task Distribution 如何识别；
- 子 Strategy 如何继承；
- 改进何时上推到 Parent；
- 是否允许兄弟 Strategy 合并。

## O2：Failure Attribution

需要继续确定：

```text
错误到底归因到：
Agent？
Prompt？
Skill？
Tool？
Edge？
Topology？
```

## O3：Mutation Search Space

V1 推荐暂时允许：

```text
Prompt Update
Skill Adjustment
Tool Adjustment
Add Existing Role
Remove Existing Role
Add / Remove Edge
Sequential / Parallel Adjustment
Conditional Agent
Retry / Replan Policy
```

暂不允许：

```text
自动创造无限新 Role
无限循环 Graph
完全自由代码生成 Workflow
开放式 Crossover
自修改 Evolution Engine
```

---

# 17. 当前形成的核心产品思想

> **任务决定 Team 的初始组织，经验决定 Team 的下一代组织。**

> **Memory 负责记住发生了什么，Evolution 负责决定以后应该改变什么。**

> **Evolution 的目标不是增加 Agent，而是在质量、成本、延迟和复杂度之间寻找更好的组织 Strategy。**
