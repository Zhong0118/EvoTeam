# EvoTeam Roadmap

> 这不是“尽快写完应用”的开发排期，而是从产品定义到可验证比赛作品的路线图。

---

# Phase -1：产品定义与汇报准备

**当前阶段**

目标：

> 先说明白我们要做什么，以及为什么值得做。

任务：

- [x] 明确赛题核心要求
- [x] 明确 openJiuwen Core 作为基础底座
- [x] 建立初步架构
- [ ] 明确最终产品定位
- [ ] 明确“自演进”的正式定义
- [ ] 明确 3 个核心创新点
- [ ] 明确 3 类实验任务
- [ ] 明确 Before / After 实验设计
- [ ] 形成第一版产品图
- [ ] 形成第一版汇报 PPT

退出条件：

团队成员能够一致回答：

1. 我们做的是什么？
2. 为什么不用固定 Workflow？
3. 为什么一定需要多 Agent？
4. 什么叫自演进？
5. 我们的创新和 openJiuwen 自带能力有什么区别？
6. 我们怎么证明演进有效？

---

# Phase 0：仓库与工程基线

目标：

> 让三个人和 Coding Agent 都可以一致开发。

任务：

- [x] GitHub 仓库
- [x] main
- [x] uv
- [x] Python 3.12
- [ ] pyproject.toml
- [ ] uv.lock
- [ ] .python-version
- [ ] .gitignore
- [ ] .env.example
- [ ] README
- [ ] DEVELOPMENT
- [ ] AGENTS
- [ ] docs 文档体系
- [ ] pytest
- [ ] Ruff
- [ ] Pyright（可稍后）

---

# Phase 1：openJiuwen 能力验证

目标：

> 先真正理解框架，而不是直接封装。

需要完成最小实验：

- [ ] openJiuwen 单 Agent
- [ ] LLM 调用
- [ ] ReActAgent
- [ ] Tool 调用
- [ ] 结构化输出
- [ ] Streaming / async 基础行为
- [ ] 明确 Context / State 工作方式

输出：

```text
examples/openjiuwen_basics/
```

退出条件：

团队至少两个人能够解释：

> openJiuwen Core 在 EvoTeam 中具体负责什么。

---

# Phase 2：EvoTeam Core

目标：

> 建立与框架解耦的核心 Domain。

实现：

- [ ] TaskSpec
- [ ] TaskProfile
- [ ] AgentSpec
- [ ] TeamSpec
- [ ] Strategy
- [ ] Run
- [ ] AgentMessage
- [ ] TraceEvent
- [ ] EvaluationResult
- [ ] EvolutionProposal

同时：

- [ ] Runtime Protocol
- [ ] Store Protocol
- [ ] Evaluator Protocol

---

# Phase 3：最小三 Agent 协作

目标：

```text
Planner
 ↓
Executor
 ↓
Critic
```

实现：

- [ ] Planner
- [ ] Executor
- [ ] Critic
- [ ] TeamOrchestrator
- [ ] Structured Message
- [ ] Trace Events

初始任务建议：

```text
Task Planning
```

因为不依赖外部搜索和代码执行。

---

# Phase 4：Evaluation First

目标：

> 先让结果可测量。

实现：

- [ ] Evaluation Rubric
- [ ] LLM Judge
- [ ] Rule-based Checks
- [ ] Failure Tags
- [ ] Token Metrics
- [ ] Latency Metrics
- [ ] Run Comparison

退出条件：

同一个任务的两个 Strategy 可以被明确比较。

---

# Phase 5：Persistence & Observability

实现：

- [ ] SQLite
- [ ] Task Store
- [ ] Run Store
- [ ] Trace Store
- [ ] Evaluation Store
- [ ] Strategy Version Store

之后才考虑：

- [ ] API
- [ ] SSE
- [ ] 简单 Web Timeline

---

# Phase 6：Prompt Evolution v1

第一版真正的 Self-Evolution。

```text
Failure Tags
 ↓
Failure Pattern
 ↓
Prompt Candidate
 ↓
Validation
 ↓
Promote / Rollback
```

实现：

- [ ] Trigger
- [ ] Proposal
- [ ] Prompt Version
- [ ] Validation Dataset
- [ ] Promotion
- [ ] Rollback

---

# Phase 7：Tool Policy Evolution

候选：

```text
算数任务
LLM → Python

搜索型任务
无 Search → Search
```

实现需建立：

- Tool Success Rate
- Tool Cost
- Tool Selection History

---

# Phase 8：Team Evolution

比赛最重要阶段之一。

实现：

- [ ] Add Agent
- [ ] Remove Agent
- [ ] Change Role
- [ ] Change Edge
- [ ] Conditional Agent
- [ ] Team Version

目标：

> 演进不只是修改 Prompt，而是改变组织结构。

---

# Phase 9：三类任务实验

### Track A：报告生成

### Track B：数据分析

### Track C：任务规划

每类任务：

- [ ] Baseline
- [ ] EvoTeam
- [ ] Before / After
- [ ] Ablation
- [ ] Cost / Latency
- [ ] Repeatability

---

# Phase 10：产品化展示

这时再投入 UI。

重点：

```text
Task
Team Graph
Timeline
Evaluation
Evolution
Generation History
```

不是优先做聊天框。

---

# Phase 11：比赛版本

需要：

- [ ] README
- [ ] Quick Start
- [ ] Demo Script
- [ ] 实验结果
- [ ] 演进案例
- [ ] 架构图
- [ ] PPT
- [ ] 演示视频
- [ ] 文档
- [ ] 可复现脚本

---

# 近期优先级

当前几天：

```text
P0 产品定义
P0 汇报材料
P0 架构
P0 实验设计

P1 环境初始化
P1 openJiuwen 学习验证

P2 代码 MVP
```

当前不要被“赶紧做页面”带偏。
