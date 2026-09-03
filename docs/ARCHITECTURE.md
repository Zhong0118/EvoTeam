# EvoTeam 架构设计草案

> 状态：v0.1 / 讨论中  
> 目的：固定模块边界，不提前锁死具体实现。

---

# 1. 架构目标

EvoTeam 架构需要同时满足：

1. 基于 openJiuwen；
2. 多 Agent 可动态组合；
3. 所有协作可观察；
4. 所有结果可评价；
5. 所有演进可版本化；
6. 所有演进可回滚；
7. 后续可扩展不同任务类型。

---

# 2. 总体分层

```text
┌─────────────────────────────────────────┐
│              Product / Web              │
│ Task / Graph / Timeline / Evolution UI  │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│            Application Layer            │
│ API / Use Cases / Run Management        │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│             EvoTeam Core                │
│                                         │
│ Task Analysis                           │
│ Team Formation                          │
│ Team Orchestration                      │
│ Evaluation                              │
│ Experience                              │
│ Evolution                               │
│ Strategy Registry                       │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│          Runtime Abstraction            │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│         OpenJiuwen Adapter              │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│        openJiuwen agent-core            │
│ Agent / Model / Tool / Workflow         │
└───────────────────┬─────────────────────┘
                    │
            LLM / Search / Code / DB
```

---

# 3. 核心模块

## 3.1 Task Analyzer

职责：

- 识别任务类型；
- 识别复杂度；
- 提取约束；
- 判断需要的能力；
- 给 Team Formation 提供结构化 Task Profile。

候选输出：

```python
class TaskProfile(BaseModel):
    task_type: str
    complexity: str
    capabilities: list[str]
    constraints: list[str]
    requires_tools: list[str]
```

---

## 3.2 Team Formation

职责：

> 决定“这次任务应该由谁来做”。

输入：

```text
Task Profile
Historical Strategy
Budget
```

输出：

```text
TeamSpec
```

第一阶段可以简单：

```text
Rule / LLM
```

后期再加入：

```text
Historical Strategy Retrieval
Bandit / Policy Selection
```

---

## 3.3 Team Orchestrator

职责：

- 创建 Agent；
- 调度 Agent；
- 管理上下文；
- 转发消息；
- 控制循环；
- 产生 TraceEvent。

默认原则：

```text
Agent 不直接互调
```

而是：

```text
Agent A
  ↓
Orchestrator
  ↓
Agent B
```

---

## 3.4 Evaluator

职责：

> 判断系统到底做得好不好。

Evaluator 不等于 Critic Agent。

### Critic

属于任务执行 Team。

### Evaluator

属于系统评价层。

Evaluator 可以结合：

- 规则；
- LLM Judge；
- Ground Truth；
- 数值校验；
- 用户反馈。

---

## 3.5 Experience Store

保存：

```text
Task
Team
Strategy
Trace
Evaluation
Failure Tags
Evolution
Metrics
```

结构化数据优先使用关系数据库。

后期语义经验检索再考虑接：

```text
agent-memory
```

---

## 3.6 Evolution Engine

职责：

```text
历史表现
 ↓
识别失败模式
 ↓
提出变更
 ↓
构造 Candidate Strategy
 ↓
交给 Validation
```

Evolution Engine 不直接覆盖当前策略。

---

## 3.7 Validation Gate

输入：

```text
Current Strategy
Candidate Strategy
Validation Tasks
```

输出：

```text
Compare Result
```

判断：

```text
Promote
or
Rollback
```

---

# 4. Strategy 是核心对象

当前推荐把一次“团队怎么做事”的完整配置抽象为：

```python
class Strategy(BaseModel):
    id: str
    version: int
    team: TeamSpec
    prompts: dict
    tool_policies: dict
    orchestration_policy: dict
    metadata: dict
```

这样演进不是：

```text
改某一段代码
```

而是：

```text
Strategy v1
→
Strategy v2
```

---

# 5. Domain Model 候选

```text
TaskSpec
TaskProfile

AgentSpec
TeamSpec
TeamEdge

Strategy

Run
AgentMessage
AgentResult
TraceEvent

EvaluationResult
FailurePattern

EvolutionProposal
ValidationResult
Generation
```

---

# 6. Runtime Abstraction

目标：

> EvoTeam Core 不应该知道 openJiuwen 具体 API。

候选：

```python
class AgentRuntime(Protocol):

    async def create_agent(self, spec: AgentSpec):
        ...

    async def invoke(self, agent, message, context):
        ...
```

实现：

```text
OpenJiuwenRuntime
```

当前比赛版本只实现这一种 Runtime。

---

# 7. Event / Trace 架构

每次运行必须可重建。

推荐事件：

```text
TASK_CREATED
TEAM_SELECTED
AGENT_CREATED
AGENT_STARTED
AGENT_MESSAGE
TOOL_CALLED
AGENT_COMPLETED
EVALUATION_STARTED
EVALUATION_COMPLETED
EVOLUTION_TRIGGERED
EVOLUTION_PROPOSED
VALIDATION_COMPLETED
STRATEGY_PROMOTED
STRATEGY_ROLLED_BACK
RUN_COMPLETED
```

前端 Timeline、实验日志和审计都基于这套 Event。

---

# 8. 数据层

## MVP

```text
SQLite
```

适合：

- 本地；
- Demo；
- 单机比赛项目。

## 后期

```text
PostgreSQL
```

不要在产品方向未定前引入：

```text
Redis
Kafka
Milvus
Elasticsearch
```

---

# 9. 前端候选

**[假设]**

```text
React
TypeScript
Vite
React Flow
ECharts
```

重点不是聊天框，而是：

```text
Agent Graph
Execution Timeline
Evaluation
Evolution Diff
Generation History
```

---

# 10. MVP 架构

第一阶段：

```text
Task
 ↓
Planner
 ↓
Executor
 ↓
Critic
 ↓
Evaluator
 ↓
Store Trace
```

注意：

此时还没有真正的 Team Evolution。

这是为了先建立：

```text
Run
Trace
Evaluation
```

---

# 11. Evolution v1

最小自演进：

```text
Failure Tags
 ↓
Prompt Evolution
 ↓
Candidate Prompt
 ↓
Validation
 ↓
Promote / Rollback
```

---

# 12. Evolution v2

加入：

```text
Tool Policy Evolution
```

---

# 13. Evolution v3

加入：

```text
Team Structure Evolution
```

例如：

```text
Planner
Executor
Critic
```

变成：

```text
Planner
Executor
Verifier
Critic
```

或者反向删除低收益 Agent。

---

# 14. 当前架构待决策

以下尚未确定：

- Team Formation 用规则还是 LLM；
- Critic 是否属于所有 Team；
- Evaluator 是单 Agent 还是多种 Evaluator 组合；
- Strategy Validation 数据集如何管理；
- Memory 何时接 agent-memory；
- 前端何时启动；
- 是否需要引入 openJiuwen WorkflowAgent；
- 哪部分借鉴 JiuwenSwarm。

所有这些应该通过讨论 / 实验决定，而不是由 Coding Agent 自动选择。
