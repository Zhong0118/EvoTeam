# EvoTeam Related Work

> 状态：v0.1  
> 目的：为 EvoTeam 的产品设计、技术路线、比赛汇报和后续论文式文档建立相关工作基线。  
> 说明：本文档关注与 EvoTeam 设计决策直接相关的代表工作，不是完整文献综述。

---

# 1. 研究问题定位

EvoTeam 处在几个研究方向的交叉点：

```text
Self-Reflective / Lifelong Agent
          │
          ├────────────┐
          ▼            ▼
Dynamic Multi-Agent   Automated Agent Design
          │            │
          └──────┬─────┘
                 ▼
       Multi-Agent Self-Evolution
                 │
                 ▼
              EvoTeam
```

EvoTeam 当前关注：

> 如何根据跨任务执行经验，对多智能体系统中的角色组合、能力配置、通信拓扑和执行策略进行可验证、可回滚的持续演进？

---

# 2. 单 Agent 反思、经验与终身学习

## Reflexion

**Reflexion: Language Agents with Verbal Reinforcement Learning**  
Shinn et al., 2023  
arXiv:2303.11366  
https://arxiv.org/abs/2303.11366

核心：

```text
Task → Feedback → Verbal Reflection → Episodic Memory → Next Attempt
```

启发：

- 不一定要更新模型参数；
- 文本反馈可成为学习信号；
- 失败经验可跨 attempt 使用。

差异：

```text
Reflexion: Individual Agent Behavior
EvoTeam: Team Organization / Coordination
```

EvoTeam 还强调 Version、Validation、Promotion、Rollback。

---

## Voyager

**Voyager: An Open-Ended Embodied Agent with Large Language Models**  
Wang et al., 2023  
arXiv:2305.16291  
https://arxiv.org/abs/2305.16291

核心：

- automatic curriculum；
- executable skill library；
- environment-feedback-driven iterative prompting。

关键启发：

```text
Experience → Reusable Capability
```

Voyager 主要积累单 Agent Skill Library；EvoTeam 计划积累 Team Strategy Library。

---

# 3. 动态 Multi-Agent Team

## DyLAN

**A Dynamic LLM-Powered Agent Network for Task-Oriented Agent Collaboration**  
Liu et al.  
arXiv:2310.02170  
https://arxiv.org/abs/2310.02170

核心问题：

```text
固定 Agent 数量
+
静态通信结构
```

DyLAN 支持：

- 动态选择 Agent；
- 多轮动态通信；
- Agent Importance；
- Early Stop。

对 EvoTeam 的启发：

- Agent 数量不应固定；
- 任务复杂度影响 Team；
- Contribution 可用于 Pruning；
- 动态 Team 可兼顾性能和效率。

差异：

```text
DyLAN: inference-time dynamic selection
EvoTeam: cross-task strategy evolution
```

---

# 4. Communication Graph Optimization

## GPTSwarm

**GPTSwarm: Language Agents as Optimizable Graphs**  
Zhuge et al., 2024  
arXiv:2402.16823  
https://arxiv.org/abs/2402.16823

核心表示：

```text
Node = LLM / Tool Operation
Edge = Information Flow
```

这为 EvoTeam 提供很自然的表示：

```text
Strategy ≈ Typed Multi-Agent Graph
```

---

## AgentPrune

**Cut the Crap: An Economical Communication Pipeline for LLM-based Multi-Agent Systems**  
Zhang et al., 2024 / ICLR 2025  
arXiv:2410.02506  
https://arxiv.org/abs/2410.02506

核心问题：

```text
Token Overhead
Communication Redundancy
```

启发：

> Evolution 不只是 Add Agent。

还应该允许：

```text
Remove Agent
Remove Edge
Conditional Agent
Reduce Communication
```

---

## Adaptive Graph Pruning

**Adaptive Graph Pruning for Multi-Agent Communication**  
Li et al., 2025  
arXiv:2506.02951  
https://arxiv.org/abs/2506.02951

联合优化：

```text
Agent Quantity
+
Communication Topology
```

其中 hard pruning 调整 Agent 数量，soft pruning 调整通信结构。

与 EvoTeam 的关系：

```text
AGP: 当前任务上的动态拓扑优化
EvoTeam: 跨任务经验驱动、可版本化的 Strategy 演进
```

---

# 5. 自动生成 / 演化 Multi-Agent System

## EvoAgent

**EvoAgent: Towards Automatic Multi-Agent Generation via Evolutionary Algorithms**  
Yuan et al., 2024 / NAACL 2025  
arXiv:2406.14228  
https://arxiv.org/abs/2406.14228

核心：

```text
Mutation
Crossover
Selection
```

启发：

```text
Evolution Operator
Candidate Pool
Selection
```

V1 不建议照搬完整遗传算法，因为搜索空间和工程风险较大。

---

## EvoMAS

**Evolutionary Generation of Multi-Agent Systems**  
Hu et al., 2026  
arXiv:2602.06511  
https://arxiv.org/abs/2602.06511

核心：

```text
Structured Configuration Generation
```

再结合：

```text
Candidate Pool
Feedback-conditioned Mutation
Crossover
Execution Trace
Experience Memory
```

重要启发：

> 不让 LLM 任意生成整个程序，而是在结构化配置空间中演进。

这非常支持 EvoTeam：

```text
Strategy = Structured Configuration
```

的设计。

---

# 6. 自动 Agent / Workflow 设计

## ADAS

**Automated Design of Agentic Systems**  
Hu et al., 2024 / ICLR 2025  
arXiv:2408.08435  
https://arxiv.org/abs/2408.08435

核心：

> 使用 Search Algorithm 在 Agentic System Design Space 中寻找更优系统。

对 EvoTeam 的启发：

```text
Search Space
Search Method
Evaluation Function
```

应该成为 Evolution Engine 三个核心设计对象。

---

## AFlow

**AFlow: Automating Agentic Workflow Generation**  
Zhang et al., ICLR 2025  
arXiv:2410.10762  
https://arxiv.org/abs/2410.10762

核心：

```text
Workflow as Code
+
Monte Carlo Tree Search
```

启发：

> Topology / Execution Policy 的优化可以看成搜索问题。

V1 不建议开放任意代码 Workflow Generation，优先做 Schema-Constrained Graph Mutation。

---

# 7. 经验驱动 Multi-Agent Self-Evolution

## Meta-Team

**Evolve as a Team: Collaborative Self-Evolution for LLM-based Multi-Agent Systems**  
Hao et al., 2026  
arXiv:2605.29790  
https://arxiv.org/abs/2605.29790

这是 EvoTeam 必须重点阅读的工作。

出发点：

> Multi-Agent 执行经验很长，跨多个 Agent 和通信链路，难以确定究竟应该改哪里。

核心：

```text
Preserve Agent-local Context
        ↓
Post-task Communication
        ↓
Distributed Evidence
        ↓
Collaborative Evolution
```

并进行：

```text
Agent Behavior
Inter-Agent Coordination
Team-Level Organization
```

多尺度演进。

直接影响 EvoTeam 的设计：

# Failure Attribution 必须成为核心问题。

EvoTeam 不能：

```text
结果错了 → 随便改 Executor Prompt
```

而应该判断：

```text
Agent？
Tool？
Prompt？
Communication Edge？
Team Structure？
```

EvoTeam 计划进一步突出：

- Strategy Family；
- Schema-constrained Strategy；
- Validation Gate；
- Promotion / Rollback；
- Cost / Complexity-aware Pruning；
- 可视化 Evolution Governance。

---

# 8. openJiuwen / JiuwenSwarm

官方仓库：

https://github.com/openJiuwen-ai/jiuwenswarm

JiuwenSwarm 当前已经包含：

- Leader / Teammate Collaboration；
- Dynamic Task Decomposition；
- SwarmFlow；
- Task Memory；
- Skill Self-Evolution；
- Reviewer Feedback Attribution；
- Swarm Skill；
- Auto Harness。

## Task Memory

JiuwenSwarm 提供：

```text
experience_retrieve
experience_learn
```

并可持久化任务经验。

这说明：

> Task Experience 本身已经是 openJiuwen 生态中的一等概念。

## Skill Evolution

JiuwenSwarm 当前演进链路大致为：

```text
Tool Error / User Correction / Reviewer Feedback
 ↓
SignalDetector
 ↓
Structured Observation
 ↓
Evolution Record
 ↓
evolutions.json
 ↓
SKILL.md
```

因此 EvoTeam 不能把以下单独当作主要创新：

```text
多 Agent
Leader 拆任务
Task Memory
Skill Evolution
失败后改 Skill
Reviewer Feedback
```

EvoTeam 需要把演进对象抬高到：

```text
Skill Evolution
        ↓
Strategy / Organization Evolution
```

重点：

```text
Topology
Version
Validation
Promotion
Rollback
Pruning
Strategy Family
Cross-task Benchmark
```

---

# 9. Self-Evolving Agent Survey

## A Survey of Self-Evolving Agents

**A Survey of Self-Evolving Agents: On Path to Artificial Super Intelligence**  
arXiv:2507.21046  
https://arxiv.org/abs/2507.21046

一个非常适合我们采用的设计框架：

```text
What to evolve?
When to evolve?
How to evolve?
```

映射到 EvoTeam：

```text
What:
Prompt / Skill / Tool / Topology

When:
Failure / Drift / Low Contribution

How:
Mutation / Search / Validation
```

---

## A Comprehensive Survey of Self-Evolving AI Agents

arXiv:2508.07407  
https://arxiv.org/abs/2508.07407

帮助我们把 EvoTeam 放到：

```text
Static Foundation Model
        ↓
Lifelong Adaptive Agent System
```

的更大研究背景中。

---

# 10. RSI：Recursive Self-Improvement

## 概念

RSI 通常强调：

> 一个系统不仅提升任务能力，还能够改进用于产生下一轮改进的自身机制。

早期代表讨论：

**From Seed AI to Technological Singularity via Recursively Self-Improving Software**  
Yampolskiy, 2015  
arXiv:1502.06512  
https://arxiv.org/abs/1502.06512

近期也有工作讨论 bounded 与 open-ended self-improvement：

**On the Limits of Self-Improving in Large Language Models**  
arXiv:2601.05280  
https://arxiv.org/abs/2601.05280

---

# 11. EvoTeam 与 RSI 的关系

EvoTeam V1：

```text
Developer fixes:
Evolution Engine
Mutation Operators
Evaluator
Validation Rules

Evolution Engine improves:
Strategy
```

因此不是严格 RSI。

更接近：

```text
Controlled Inter-task Self-Evolution
```

未来如果支持：

```text
Mutation Policy Evolution
Evaluator Evolution
Search Strategy Evolution
Evolution Trigger Evolution
```

并让新的 Evolution Engine 继续产生更好的 Evolution Engine，才逐步接近：

```text
Bounded Recursive Self-Improvement
```

比赛中不建议宣称“实现 RSI”。

更稳妥的表达：

> EvoTeam 借鉴 Self-Evolving Agent 与 Recursive Self-Improvement 的思想，但采用受约束、可验证、可回滚的 Strategy Evolution，优先保证演进的可控性和可解释性。

---

# 12. Related Work 导出的 EvoTeam 设计原则

## 系统 Graph 化

来自：

```text
GPTSwarm
AgentPrune
AGP
```

因此：

```text
Strategy ≈ Typed Multi-Agent Graph
```

## Evolution 结构化

来自：

```text
EvoMAS
ADAS
```

因此：

```text
Schema-Constrained Mutation
```

优于自由重写整个系统。

## Experience 必须归因

来自：

```text
Meta-Team
```

因此 Failure Attribution 不是附属功能。

## Evolution 同时允许增长和剪枝

来自：

```text
DyLAN
AgentPrune
AGP
```

因此 Add 和 Remove 同等重要。

## Memory 不等于 Evolution

来自：

```text
Reflexion
Voyager
JiuwenSwarm Task Memory
```

Memory 可以记录和检索，但 EvoTeam 还必须完成：

```text
Diagnosis
Mutation
Validation
Promotion
```

---

# 13. 当前 EvoTeam 的差异化组合

目前不声称“学术上没人做过”，而是寻找比赛作品最有价值的组合：

```text
Task-adaptive Team Formation
+
Cross-task Structured Experience
+
Strategy Family
+
Topology / Skill / Tool Mutation
+
Failure Attribution
+
Validation Gate
+
Promotion / Rollback
+
Complexity-aware Pruning
+
Evolution Visualization
```

特别值得形成产品概念的是：

# Evolution Governance

即：

> 自演进系统不仅需要会改，还需要管理为什么改、改了什么、是否应该上线、是否需要回滚。

---

# 14. 阅读优先级

## P0

1. Meta-Team
2. JiuwenSwarm Skill Self-Evolution
3. JiuwenSwarm Task Memory
4. EvoMAS
5. GPTSwarm

## P1

6. DyLAN
7. AgentPrune
8. Adaptive Graph Pruning
9. ADAS
10. AFlow

## P2

11. Reflexion
12. Voyager
13. Self-Evolving Agent Surveys
14. RSI literature

---

# 15. PPT 中如何呈现 Related Work

不要放成十几篇论文标题列表。

建议用研究坐标图，突出：

```text
Memory / Skill
Dynamic Team
Topology Optimisation
Agent System Search
Experience-driven MAS Evolution
```

最后落到：

> EvoTeam 关注的是将这些能力组织成“可治理、可版本化、可验证”的组织级 Strategy Evolution。
