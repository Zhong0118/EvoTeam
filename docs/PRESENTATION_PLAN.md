# EvoTeam 阶段汇报 PPT 规划

> 目标：几天后的阶段汇报。  
> 当前重点不是证明产品已经做完，而是证明“问题理解清楚、方案有价值、技术路线可信、实验可验证”。

---

# 1. 汇报目标

听众应该在结束后记住三件事：

1. 传统 Multi-Agent 的问题是“固定团队无法持续学习”；
2. EvoTeam 的核心是“可验证的组织自演进”；
3. 我们不是重做 openJiuwen，而是在其上构建 Evolution Layer。

---

# 2. 推荐 PPT 结构

## Slide 1：标题

```text
EvoTeam
基于 openJiuwen 的自演进多智能体协作系统
```

副标题候选：

```text
让 Agent Team 像组织一样学习、协作与演进
```

---

## Slide 2：问题背景

传统 Agent Team：

```text
固定角色
固定数量
固定 Workflow
人工 Prompt
任务之间没有持续学习
```

提出：

> 为什么 Agent Team 每次都像“新组建的临时团队”？

---

## Slide 3：赛题要求

压缩成：

```text
3+ Agent
协作
自演进
Before vs After
3 类任务
可解释
可视化
```

强调：

```text
自演进 = 核心
```

---

## Slide 4：我们的理解

三层：

```text
Agent 能运行
      ↓
Multi-Agent 能协作
      ↓
Agent Team 能持续演进
```

前两层是基础，第三层才是项目重点。

---

## Slide 5：EvoTeam 一句话

> 一个建立在 openJiuwen Core 上的自演进 Agent Team 组织层。

架构：

```text
EvoTeam
 ↓
openJiuwen Core
 ↓
LLM / Tool
```

---

## Slide 6：核心闭环

```text
Task
↓
Team Formation
↓
Execution
↓
Evaluation
↓
Experience
↓
Evolution
↓
Validation
↓
Next Generation
```

这页非常关键。

---

## Slide 7：三个演进维度

```text
Prompt Evolution
Tool Evolution
Team Evolution
```

其中突出：

```text
Team Evolution
```

---

## Slide 8：组织演进示例

Before：

```text
Planner
Executor
Critic
```

失败：

```text
numeric_error
```

After：

```text
Planner
Executor
CodeVerifier
Critic
```

---

## Slide 9：不是无脑加 Agent

展示：

```text
Add Agent
Remove Agent
Conditional Agent
```

强调目标：

```text
Quality / Cost / Latency
```

共同优化。

---

## Slide 10：Validation Gate

```text
Current
 ↓
Proposal
 ↓
Candidate
 ↓
Validation
 ↙       ↘
Promote  Rollback
```

这是非常适合答辩的创新点。

---

## Slide 11：系统架构

四层：

```text
Product
EvoTeam Core
OpenJiuwen Adapter
openJiuwen Core
```

---

## Slide 12：三类任务

```text
报告生成
数据分析
任务规划
```

展示不同 Team。

---

## Slide 13：实验设计

```text
Single Agent
Fixed Multi-Agent
EvoTeam
```

以及：

```text
V0
V1 Prompt Evo
V2 + Tool Evo
V3 + Team Evo
```

---

## Slide 14：评价指标

```text
Quality
Success Rate
Token
Latency
Agent Count
Retry
```

---

## Slide 15：开发路线

当前：

```text
Product Design
Architecture
Experiment Design
```

之后：

```text
openJiuwen MVP
→
3 Agent
→
Evaluation
→
Evolution
→
Web
→
Experiments
```

---

## Slide 16：预期成果

- EvoTeam 系统；
- 三类可复现实验；
- 自演进 Before / After；
- Agent Team 可视化；
- Strategy Generation 历史；
- 完整项目文档。

---

# 3. 汇报时不要过度承诺

当前阶段不要说：

```text
“我们已经实现动态 Swarm”
“我们已经实现 RL 自演进”
“系统可以支持任意复杂任务”
```

如果还没完成，应说：

```text
我们已经确定技术路线 / 实验方案，
下一阶段将完成...
```

---

# 4. 近期需要补齐的 PPT 素材

- [ ] 一张“传统 Agent Team 问题”图
- [ ] 一张 EvoTeam 总闭环图
- [ ] 一张系统架构图
- [ ] 一张 Team Evolution Before / After 图
- [ ] 一张 Validation Gate 图
- [ ] 一张 Roadmap
- [ ] 一张实验矩阵
- [ ] 一张 openJiuwen 与 EvoTeam 边界图

---

# 5. 汇报最值得强调的句子

候选：

> 我们关注的不是“让更多 Agent 一起工作”，而是“让 Agent Team 根据经验改变下一次如何工作”。

以及：

> 自演进不是失败后再试一次，而是让历史经验改变未来策略。
