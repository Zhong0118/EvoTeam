# EvoTeam 产品愿景与产品假设

> 本文档不是最终 PRD，而是产品讨论的“共同白板”。

---

# 1. 一句话愿景

**[假设]**

> EvoTeam 让 Agent Team 像一个真实组织一样，能够根据任务和经验动态组队、协作、评价并持续演进。

---

# 2. 我们真正想解决的问题

现有 Agent Framework 已经可以：

- 创建 Agent；
- 调用模型；
- 调工具；
- 运行 Workflow；
- 多 Agent 通信。

因此 EvoTeam 不应该证明：

> “我们也能做三个 Agent。”

真正值得做的是：

> 一个 Agent Team 能不能从历史任务中形成组织经验，并让这些经验对未来任务产生可验证的结构性影响？

---

# 3. 当前核心价值主张

候选表达：

### 版本 A：比赛表达

> 面向复杂任务的可验证自演进多智能体协作系统。

### 版本 B：产品表达

> An adaptive operating layer for teams of AI agents.

### 版本 C：研究表达

> Experience-driven organization evolution for multi-agent systems.

当前尚未决定最后使用哪一个。

---

# 4. 产品核心对象

EvoTeam 可能不是“聊天产品”。

它真正管理的对象可能是：

```text
Task
Agent
Team
Strategy
Run
Trace
Evaluation
Experience
Evolution
Generation
```

因此产品主界面未来更可能是：

```text
Task Console
+
Agent Graph
+
Execution Timeline
+
Evaluation
+
Evolution History
```

而不是单纯：

```text
Chat Window
```

---

# 5. 产品核心故事

### Generation 0

```text
Planner
   ↓
Executor
   ↓
Critic
```

连续运行任务后：

```text
numeric_error × 5
```

系统发现：

> 失败高度集中在数值验证。

系统提出：

```text
Add CodeVerifier
```

形成 Generation 1：

```text
Planner
   ↓
Executor
   ↓
CodeVerifier
   ↓
Critic
```

验证结果：

```text
Quality ↑
Error Rate ↓
Cost + small
```

因此 Promote。

随后发现 Critic 对某类简单任务贡献有限：

```text
Quality Gain ≈ 0
Cost ↑
Latency ↑
```

下一代策略可能变成：

```text
Critic = conditional
```

这就是我们理想中的“组织演进”。

---

# 6. 当前三个产品假设

## H1：动态组织比固定 Workflow 更适合异构任务

需要通过：

```text
固定 Team
vs
任务驱动 Team
```

验证。

---

## H2：历史失败模式可以指导未来 Team 结构

例如：

```text
numeric_error
→
CodeVerifier
```

需要证明：

不是偶然。

---

## H3：Evolution Gate 比直接自修改更稳定

比较：

```text
直接改 Prompt / Team
vs
Candidate → Validation → Promote/Rollback
```

---

# 7. 我们暂时不确定的产品问题

以下问题应该留到团队讨论，不要由代码提前决定。

### Q1

EvoTeam 最终是：

- 一个面向开发者的 Agent Team 平台？
- 一个比赛型复杂任务应用？
- 一个“组织演进引擎”中间件？
- 一个研究原型 + 可视化系统？

**[待定]**

---

### Q2

用户是否需要手工编辑 Team？

候选：

- 完全自动；
- 自动生成 + 人工调整；
- 提供专家模式。

**[待定]**

---

### Q3

演进是：

- 每 N 个任务自动触发；
- 当失败模式超过阈值触发；
- 用户手动触发；
- 三种都支持。

**[待定]**

---

### Q4

Team Formation 初期采用：

- 规则；
- LLM Planner；
- 历史 Strategy 检索；
- 混合方式。

**[待定]**

---

### Q5

是否应该展示 Agent 内部完整思考过程？

当前倾向：

> 不展示私有推理，而展示结构化计划、动作、工具、评价和演进证据。

**[假设]**

---

# 8. 产品设计原则

1. **Evolution must be visible**  
   用户能看见系统为什么变化。

2. **Evolution must be measurable**  
   不能只说“变好了”。

3. **Evolution must be reversible**  
   新策略可以失败并回滚。

4. **More agents is not always better**  
   系统应该能够增加，也能够减少 Agent。

5. **History must matter**  
   如果历史任务完全不影响未来任务，就谈不上持续演进。

6. **Framework capability ≠ product innovation**  
   openJiuwen 已经提供的能力不能直接当作我们的创新点。

---

# 9. 未来产品页面候选

## 页面 1：Task Workspace

```text
Task Input
Task Type
Constraints
Budget
Run
```

## 页面 2：Agent Team

```text
Current Team Graph
Role
Prompt Version
Tools
Model
```

## 页面 3：Execution

```text
Timeline
Messages
Tool Calls
Latency
Tokens
```

## 页面 4：Evaluation

```text
Overall Score
Dimension Scores
Failures
Evidence
```

## 页面 5：Evolution

```text
Trigger
Evidence
Before
Candidate
Validation
Promote / Rollback
```

## 页面 6：Generations

```text
Gen 0 → Gen 1 → Gen 2
```

---

# 10. 当前阶段不要做什么

在产品方向未稳定前，不要急于：

- 做复杂聊天 UI；
- 做几十种 Agent；
- 做分布式 Swarm；
- 上强化学习；
- 上生产级部署；
- 接一堆模型；
- 做插件市场；
- 做账号系统。

当前应该优先回答：

> 我们的“自演进”到底是什么？
