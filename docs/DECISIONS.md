# EvoTeam 决策记录

> 用于记录重要产品与架构选择。  
> 避免几周后团队忘记“为什么当时这么设计”。

---

# D-001：Python 使用 3.12

状态：

```text
Accepted
```

原因：

- 团队当前本地环境已有 Python 3.12；
- openJiuwen Core 支持该版本；
- 避免额外维护 3.11。

影响：

```text
pyproject.toml
.python-version
DEVELOPMENT.md
CI
```

---

# D-002：使用 uv 管理 Python 项目

状态：

```text
Accepted
```

不使用 Conda 管理 EvoTeam 项目依赖。

原因：

- 依赖声明统一；
- lockfile；
- 团队环境复现；
- Coding Agent / CI 使用简单。

---

# D-003：第一阶段基于 openJiuwen Core

状态：

```text
Accepted
```

当前不直接以：

```text
agent-studio
jiuwenswarm
```

作为项目主体。

原因：

- Core 更适合作为底层 SDK；
- EvoTeam 需要自己控制 Team Formation / Evaluation / Evolution；
- 便于区分官方能力与项目创新。

---

# D-004：仓库初始化阶段只使用 main

状态：

```text
Accepted
```

等进入多人并行功能开发后再采用：

```text
feat/*
fix/*
docs/*
```

短生命周期分支。

不采用：

```text
每人一个永久分支
```

---

# D-005：先产品设计，再大规模编码

状态：

```text
Accepted
```

近期优先级：

```text
产品定义
架构
实验
PPT
```

高于：

```text
复杂 UI
大量 Agent
生产部署
```

---

# D-006：EvoTeam Core 与 openJiuwen 解耦

状态：

```text
Proposed / 高优先级
```

候选方式：

```text
Runtime Protocol
      ↓
OpenJiuwen Adapter
```

待 MVP 验证后正式 Accepted。

---

# D-007：自演进必须经过 Validation Gate

状态：

```text
Proposed / 高优先级
```

原则：

```text
Proposal
→ Candidate
→ Validation
→ Promote / Rollback
```

不允许 LLM 直接覆盖当前 Strategy。

---

# D-008：产品不优先做聊天界面

状态：

```text
Proposed
```

更重要的产品页面：

```text
Agent Graph
Timeline
Evaluation
Evolution
Generations
```

---

# 待决策清单

## P-001

最终产品形态：

```text
开发者平台
研究原型
比赛复杂任务平台
组织演进引擎
```

---

## P-002

第一版 Team Formation：

```text
Rule
LLM
Hybrid
```

---

## P-003

第一版演进是否只做 Prompt，还是直接带 Team Evolution？

---

## P-004

第一版三类任务的具体数据集与评测方式。

---

## P-005

前端启动时间。

---

# 使用方式

当团队做出重要决定时新增：

```text
D-009
D-010
...
```

至少写：

```text
Decision
Status
Reason
Alternatives
Impact
```

不要只在微信群 / 口头讨论里决定架构。
