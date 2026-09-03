# EvoTeam PPT Storyline V1

> 目标：近期阶段汇报。  
> 重点不是假装系统已经全部实现，而是证明：问题理解清楚、方案有创新、架构可信、实验可验证。

## 核心句

> **我们不是只构建一支 Agent Team，而是让这支 Team 根据经验学会如何重新组织自己。**

英文：

> **Build a team that learns how to organize itself.**

## 推荐故事线

### Slide 1 — 标题

**EvoTeam**

> 基于 openJiuwen 的经验驱动自演进多智能体组织系统

### Slide 2 — 问题

传统 Multi-Agent：

```text
固定角色
固定数量
固定 Workflow
人工 Prompt
任务结束后经验消失
```

问题：

> 为什么 Agent Team 每接一个新项目，都像一支没有组织记忆的临时团队？

### Slide 3 — 比赛真正难点

```text
3+ Agent 是基础
Self-Evolution 才是核心
```

强调：

- Before vs After
- 可解释
- 可复现

### Slide 4 — Retry ≠ Evolution

Retry：

```text
任务内
失败后重做
不改变未来
```

Evolution：

```text
跨任务
经验持久化
改变 Strategy
版本化
验证
回滚
```

### Slide 5 — 公司类比

```text
Task = 项目
Agent = 员工
Role = 岗位
Skill = 专业能力
Tool = 工作工具
Team = 项目组
Strategy = 组织与工作方法
Experience = 组织经验
Evolution = 组织调整
```

### Slide 6 — EvoTeam 与 openJiuwen

openJiuwen：

```text
Agent 怎么运行
Model / Tool 怎么调用
```

EvoTeam：

```text
谁参与
怎么协作
哪里失败
怎么改变
是否换代
```

### Slide 7 — 核心对象 Strategy

```text
Strategy =
Role
+ Skill
+ Tool
+ Prompt
+ Topology
+ Execution Policy
```

### Slide 8 — 任务决定初始组织

```text
Task
→ Task Signature
→ Strategy Router
→ Team Formation
```

### Slide 9 — Strategy Family

```text
Report
├── General
├── News
└── Academic
```

讲：

```text
向下特化
向上泛化
```

### Slide 10 — 经验三层

```text
Event
↓
Run
↓
Evolution Window
```

一句话：

> Memory 记录过去，Evolution 改变未来。

### Slide 11 — Failure Attribution

错误可能来自：

```text
Analyst
Verifier
Planner
Tool
Topology
```

所以：

```text
Rule + Trace + LLM
```

做 Evidence-Based Attribution。

### Slide 12 — Mutation Candidate

同一 Failure：

```text
A 改 Prompt
B 强制 Tool
C 加 Verifier
```

强调：

> 不直接修改线上 Strategy。

### Slide 13 — Validation Gate

```text
Current Strategy ─┐
                  ├→ Same Validation Set
Candidate ────────┘
```

比较：

```text
Quality
Cost
Latency
Complexity
```

结论：

> 新旧方案做同一套考试，收益足够大才换代。

### Slide 14 — Growth + Pruning

展示：

```text
Add Agent
Remove Agent
Remove Edge
Conditional Agent
```

核心：

> Evolution ≠ More Agents  
> Evolution = Better Organization

### Slide 15 — 完整闭环

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

旁边放：

> 任务决定初始组织。  
> 证据决定问题归因。  
> 验证决定组织是否换代。

### Slide 16 — Related Work

按研究方向而不是论文列表：

```text
Memory / Reflection
Dynamic Team
Graph Optimization
Agent System Search
MAS Self-Evolution
```

落点：

> EvoTeam 聚焦可治理、可版本化、可验证的组织级 Strategy Evolution。

### Slide 17 — JiuwenSwarm 边界

JiuwenSwarm：

- Leader / Teammate
- Task Memory
- Skill Evolution
- SwarmFlow

EvoTeam：

- Strategy Family
- Topology Evolution
- Failure Attribution
- Validation Gate
- Promotion / Rollback
- Organization Pruning
- Cross-task Benchmark

### Slide 18 — 实验

Baseline：

```text
Single Agent
Fixed Multi-Agent
Dynamic Team
EvoTeam
```

三类 Benchmark：

```text
Report
Data
Planning
```

### Slide 19 — 预期实验图

- Before vs After
- Generation Curve
- Quality vs Cost Pareto
- Attribution Accuracy
- Agent / Edge Count
- Promotion / Rejection History

### Slide 20 — 当前进度

当前：

```text
产品机制 ✅
架构设计 ✅
实验方案 ✅
Related Work ✅
```

下一阶段：

```text
openJiuwen Core 验证
→ EvoTeam Core
→ Baseline
→ Evaluation
→ Evolution
→ Visualization
```

### Slide 21 — 结束

> **We do not only build an Agent Team.  
> We build a Team that learns how to organize itself.**
