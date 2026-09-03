# AGENTS.md

> 本文件是 EvoTeam 仓库中所有 Coding Agent、自动化编程助手和贡献者必须遵守的开发约束。

---

# 1. 你的角色

你是 EvoTeam 项目的实现者，不是产品负责人。

你的职责是：

- 阅读现有文档；
- 理解当前 Issue / Task；
- 在明确边界内实现；
- 编写测试；
- 汇报修改内容与风险。

你不应该擅自：

- 重定义产品目标；
- 替换技术栈；
- 引入新的 Agent Framework；
- 改变系统核心架构；
- 把一个小任务扩张成“大重构”。

---

# 2. 开发前必须阅读

开始任何功能开发前，至少阅读：

```text
README.md
DEVELOPMENT.md
AGENTS.md
docs/PROJECT.md
docs/ARCHITECTURE.md
docs/ROADMAP.md
```

如果任务涉及自演进或实验，还必须阅读：

```text
docs/EXPERIMENTS.md
docs/DECISIONS.md
```

---

# 3. 当前技术基线

**[确定]**

```text
Python: 3.12
Package Manager: uv
Agent Framework: openJiuwen Core
Backend Candidate: FastAPI
Frontend Candidate: React + TypeScript
```

依赖管理统一使用：

```bash
uv add ...
uv add --dev ...
uv sync
uv run ...
```

不要使用：

```bash
pip install ...
conda install ...
```

来管理项目正式依赖。

---

# 4. openJiuwen 使用边界

**[确定]**

EvoTeam 基于 `openJiuwen Core` 构建。

原则：

```text
EvoTeam Core
      │
      ▼
Runtime Abstraction
      │
      ▼
OpenJiuwen Adapter
      │
      ▼
openJiuwen
```

只有明确的 openJiuwen Adapter / Integration 层允许直接：

```python
import openjiuwen
```

以下模块不应该直接依赖 openJiuwen：

```text
core
evaluation
evolution
memory（结构化经验层）
domain models
```

目的：

- 避免业务逻辑绑死框架；
- 便于测试；
- 便于后期升级 openJiuwen；
- 便于清楚说明哪些能力属于 EvoTeam。

---

# 5. 当前禁止擅自引入

除非 Issue 明确要求，否则不要主动引入：

```text
LangGraph
AutoGen
CrewAI
Kafka
Redis
Kubernetes
Microservices
Celery
RL/PPO/GRPO 训练框架
大型向量数据库
复杂分布式基础设施
```

不要因为“更先进”就增加复杂度。

---

# 6. 核心领域规则

## 6.1 Agent 不应直接互相调用

当前默认通信方式：

```text
Agent
  ↓
TeamOrchestrator
  ↓
Agent
```

Agent 间通信由 Orchestrator 管理和记录。

这样才能保证：

- 可观察；
- 可记录；
- 可回放；
- 可评估；
- 可解释。

---

## 6.2 Agent 输出优先结构化

优先使用 Pydantic Schema。

禁止依赖：

```text
“让下一个 Agent 自己读自然语言猜结构”
```

示例：

```python
class CriticResult(BaseModel):
    score: float
    passed: bool
    issues: list[str]
    failure_tags: list[str]
```

---

## 6.3 Prompt 必须可版本化

不要长期把 Prompt 大段写死在业务 Python 文件中。

推荐：

```text
prompts/
├── planner/
│   ├── v1.md
│   └── v2.md
├── executor/
└── critic/
```

演进相关 Prompt 修改必须能够：

- 查看版本；
- 比较差异；
- 回滚。

---

## 6.4 所有运行必须可追踪

核心执行步骤应该产生统一 Event，例如：

```text
TASK_CREATED
TEAM_CREATED
AGENT_STARTED
AGENT_COMPLETED
AGENT_MESSAGE
TOOL_CALLED
EVALUATION_COMPLETED
EVOLUTION_TRIGGERED
EVOLUTION_PROPOSED
STRATEGY_PROMOTED
STRATEGY_ROLLED_BACK
```

---

# 7. 自演进约束

**[确定]**

EvoTeam 中：

```text
Retry != Evolution
```

以下行为本身不能被称为“自演进”：

- 失败后重新生成一次；
- Critic 要求 Executor 重答；
- 同一个 Prompt 多跑几次；
- 临时增加上下文。

真正的演进至少应满足：

```text
历史证据
   ↓
提出变更
   ↓
形成新版本
   ↓
验证
   ↓
Promote / Rollback
   ↓
影响未来任务
```

---

## 7.1 Evolution 不得直接修改线上策略

必须：

```text
Current Strategy
      ↓
Evolution Proposal
      ↓
Candidate Strategy
      ↓
Validation
      ↓
Promote / Rollback
```

禁止：

```text
LLM 修改 Prompt → 直接覆盖当前版本
```

---

# 8. 实验优先于“看起来更聪明”

如果实现涉及：

- Prompt Evolution
- Tool Evolution
- Team Evolution

必须考虑如何测量：

```text
Before
vs
After
```

重要指标至少包括：

- 任务质量；
- 成功率；
- Token / 成本；
- 延迟；
- Agent 数量；
- Retry 次数。

---

# 9. 代码修改原则

每次任务：

1. 只实现当前 Scope；
2. 尽量小改；
3. 不做无关重构；
4. 保持已有接口兼容；
5. 新功能补测试；
6. 文档和实现不一致时必须指出；
7. 不确定架构时停止“猜”，在报告中标记待决策。

---

# 10. 完成任务前必须执行

当前项目配置完成后，至少执行：

```bash
uv sync
uv run pytest
uv run ruff check .
```

如果已经配置 Pyright：

```bash
uv run pyright
```

---

# 11. 完成任务后的汇报格式

Coding Agent 完成任务后必须汇报：

```text
## 完成内容
- ...

## 修改文件
- ...

## 关键设计决策
- ...

## 测试
- uv run pytest: ...
- uv run ruff check .: ...

## 尚存风险
- ...

## 未完成 / 未处理
- ...
```

不要只说：

```text
“Done ✅”
```

---

# 12. Git 原则

当前仓库初始化阶段允许直接完善 `main` 基础文档和项目骨架。

进入正式多人功能开发后：

```text
main
  ↑
Pull Request
  ↑
feat/<task>
```

分支属于任务，不属于个人。

---

# 13. 最重要的约束

> 不要替团队做尚未做出的产品决策。

如果文档标记为：

```text
[待定]
[假设]
```

实现时不要擅自把它变成事实。

EvoTeam 当前首先是一个需要被验证的产品与研究方案，其次才是一个代码仓库。
