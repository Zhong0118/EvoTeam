# EvoTeam 项目定义

## 1. 项目背景

当前多智能体系统已经能够用于代码生成、科研辅助、商业分析、数据处理和复杂任务规划。

但传统 Agent Team 往往存在：

1. Agent 角色和数量固定；
2. 协作策略依赖人工设计；
3. 每次任务几乎从零开始；
4. 系统难以根据历史表现持续调整自身；
5. 很多“自反思”只是单次任务内 Retry，并不会影响未来行为。

EvoTeam 希望探索：

> Agent Team 是否可以像一个组织一样，根据任务类型、历史表现和失败模式，持续改变自己的结构与策略。

---

## 2. 赛题约束

当前项目面向“基于 openJiuwen 构建具备自演进能力的多智能体协作系统”赛题。

必须满足：

- 至少 3 类不同功能 Agent；
- 有明确 Agent 协作机制；
- 必须体现自演进过程；
- 必须展示优化前 vs 优化后；
- 至少覆盖 3 类可复现任务；
- 输出结构化、可解释；
- Agent 协作过程可视化属于加分方向。

---

## 3. 当前项目定位

**[假设]**

EvoTeam 不是：

- 一个普通聊天机器人；
- 一个固定 Workflow；
- 一个 openJiuwen Studio 插件；
- 一个重新实现的 Agent Framework；
- 一个仅仅会自动改 Prompt 的 Demo。

EvoTeam 当前定位：

> 一个建立在 openJiuwen Core 之上的“自演进 Agent Team 组织层”。

核心能力候选：

```text
Task Understanding
      ↓
Dynamic Team Formation
      ↓
Multi-Agent Collaboration
      ↓
Evaluation
      ↓
Experience Accumulation
      ↓
Evolution
      ↓
Validation
      ↓
Next-generation Strategy
```

---

## 4. openJiuwen 在项目中的角色

**[确定]**

第一阶段主要使用：

```text
openJiuwen Core
```

openJiuwen 负责：

- Agent 基础执行；
- LLM 调用；
- Tool 调用；
- Workflow / ReAct Agent 能力；
- Agent Runtime 基础能力。

EvoTeam 负责：

- Team 形成；
- Team 调度；
- 协作协议；
- 评价；
- 经验记录；
- 演进触发；
- Strategy 版本管理；
- Promote / Rollback；
- 演进可解释性。

---

## 5. 核心研究问题

项目后续所有产品与技术讨论应尽量围绕以下问题。

### RQ1：什么时候需要多 Agent？

需要证明：

> Multi-Agent 不只是“Agent 越多越好”。

需要找到：

- 单 Agent 适合的任务；
- 3 Agent 适合的任务；
- 增加专业 Agent 真正产生收益的条件。

---

### RQ2：Team 应该如何动态形成？

可能考虑：

- 任务类型；
- 复杂度；
- 工具需求；
- 历史成功策略；
- Token / 延迟预算；
- 失败风险。

---

### RQ3：什么才算“自演进”？

当前定义候选：

> 系统根据历史任务中的可验证证据，生成可版本化的协作策略变更，并通过验证后影响未来任务。

---

### RQ4：系统可以演进什么？

候选维度：

1. Prompt；
2. Tool Policy；
3. Agent Role；
4. Agent 数量；
5. Team Graph；
6. 协作顺序；
7. Strategy Selection Policy。

---

### RQ5：如何避免“越演进越复杂”？

演进目标不仅是质量最大化，还需要考虑：

- Token；
- Cost；
- Latency；
- Agent Count；
- Retry；
- 稳定性。

因此可能存在：

```text
增加 Agent
```

也可能存在：

```text
删除 Agent
```

---

## 6. 当前核心闭环

```text
Task
 ↓
Analyze
 ↓
Select / Build Team
 ↓
Execute
 ↓
Evaluate
 ↓
Record Experience
 ↓
Detect Failure Pattern
 ↓
Generate Evolution Proposal
 ↓
Validate Candidate
 ↓
Promote / Rollback
 ↓
Future Task
```

---

## 7. 三类目标任务

当前先采用赛题本身最自然的三类：

### A. 报告生成

重点观察：

- 信息完整性；
- 结构；
- 事实一致性；
- 引用质量。

### B. 数据分析

重点观察：

- 计算正确性；
- 指标覆盖；
- 结论一致性；
- 洞察质量。

### C. 任务规划

重点观察：

- 约束满足；
- 可执行性；
- 风险覆盖；
- 资源合理性。

---

## 8. 成功标准

EvoTeam 最终成功不等于：

```text
“能跑一个漂亮 Demo”
```

而应该至少证明：

1. 系统具有多 Agent 协作；
2. Team 可以针对任务变化；
3. 历史经验可以影响未来 Strategy；
4. 演进有 Before / After；
5. 演进有明确证据；
6. 演进可以回滚；
7. 至少 3 类任务可复现；
8. 演进收益可以量化。
