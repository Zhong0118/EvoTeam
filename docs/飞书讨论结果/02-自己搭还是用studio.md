<title>自己搭还是用studio</title>

对，我建议你们现在就把这个边界想清楚。**我的明确建议是：以 openJiuwen 的 Python SDK `agent-core` 作为 Agent 执行底座，在它上面实现我们自己的 EvoTeam 自演进引擎，再做自己的 Web 页面；同时把架构设计成“可扩展到其他 Agent 框架”，但比赛版本默认、重点、完整支持 openJiuwen。**

这其实是四种方案里最平衡的一种。

官方本身就是分层设计的：`Agent Studio` 是低代码可视化开发平台，`agent-core` 是 Python Agent SDK / 核心执行引擎，`agent-runtime` 负责后续服务化部署。也就是说，Studio 并不是使用 openJiuwen 的必经入口。([GitCode](https://gitcode.com/openJiuwen?utm_source=chatgpt.com))

## 先把几个东西的关系搞清楚

你现在看到的“九问 Web 页面”，其实不要理解成：

```Plain Text
openJiuwen = 那个网页
```

更准确是：

```Plain Text
                  openJiuwen 生态
                       │
       ┌───────────────┼───────────────┐
       │               │               │
 Agent Studio       agent-core     agent-runtime
    Web平台          Python SDK       部署运行
       │               │               │
 低代码搭Agent      写代码搭Agent      服务化Agent
```

官方对 Studio 的定位就是零代码/低代码的 Agent 和 Workflow 开发平台，而 Core 则直接提供 Agent 创建、Workflow 编排、模型调用、Tool、Prompt 调优和运行时能力。(GitCode)

所以：

> **我们基于 Python SDK 写，是非常正统的“基于 openJiuwen 构建”。**

甚至从这个比赛来看，我觉得比直接在 Studio 拖工作流**更合适**。

---

# 为什么我不建议直接基于九问 Studio 页面做？

因为你们的核心创新是：

> **动态组织 + 自演进。**

而低代码 Studio 天然更适合：

```Plain Text
拖几个节点
↓
连线
↓
配置 Agent
↓
运行 Workflow
```

例如：

```Plain Text
Planner → Analyst → Critic
```

这很好做。

但我们后面想做的是：

```Plain Text
              当前 Team
                 │
                 ▼
         Execution Trace
                 │
                 ▼
          Evolution Engine
                 │
       ┌─────────┼─────────┐
       ↓         ↓         ↓
     改Prompt   换Tool    改组织结构
                           │
                    ┌──────┴──────┐
                    ↓             ↓
                  增Agent        删Agent
                    │
                    ▼
                新 Team Graph
```

这种东西如果强行塞进一个现成的低代码 Web 平台，很容易受 Studio 自己的数据结构、前端、Workflow 模型限制。

而且答辩的时候还有一个问题：

> “你们自己做了什么？”

如果整个 UI 都是九问 Studio，评委看到的是：

```Plain Text
九问Studio
 +
几个工作流
```

你们项目辨识度会变弱。

---

# 所以我的推荐架构是这样

## EvoTeam 自己是一个完整 Web 应用

但执行 Agent 的时候：

> **真正使用 openJiuwen Core。**

```Plain Text
                        用户
                         │
                         ▼
              ┌─────────────────────┐
              │    EvoTeam Web      │
              │   我们自己的前端     │
              └──────────┬──────────┘
                         │
                    REST / SSE
                         │
                         ▼
              ┌─────────────────────┐
              │   EvoTeam Backend   │
              │      FastAPI        │
              └──────────┬──────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
 Task Analyzer     Evolution Engine    Evaluator
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
                  Team Orchestrator
                         │
                         ▼
              ┌─────────────────────┐
              │ openJiuwen Adapter  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ openJiuwen agent-core│
              │                     │
              │ ReActAgent          │
              │ WorkflowAgent       │
              │ Tool                │
              │ Model               │
              │ Prompt              │
              │ Runtime             │
              └─────────────────────┘
```

这就是我认为最舒服的边界。

---

# 举一个具体例子

比如我们定义一个 Research Agent。

不要自己从零写：

```Python
class ResearchAgent:
    while True:
        response = call_llm(...)
```

而是：

```Plain Text
EvoTeam 定义：

AgentSpec
- role = researcher
- prompt = xxx
- tools = [search]
- model = qwen
```

然后交给：

```Plain Text
OpenJiuwenAdapter
```

转换成九问的：

```Plain Text
ReActAgent
+
Tool
+
Model
+
Prompt
```

最终运行。

所以：

```Plain Text
我们负责：
Agent应该是什么
Agent什么时候出现
Agent怎么合作
Agent什么时候被删除
策略什么时候进化

openJiuwen负责：
Agent怎么真正运行
LLM怎么调用
Tool怎么执行
Workflow怎么跑
状态怎么管理
```

这个分工非常漂亮。

---

# 更进一步：我建议做 Adapter 层

这是你刚才提到：

> “还是做成一个通用平台，不仅局限于九问？”

我的答案是：

> **设计上通用，比赛实现上以 openJiuwen 为第一公民。**

不是：

```Plain Text
EvoTeam
  ↓
死死绑定 openJiuwen
```

也不要现在就：

```Plain Text
EvoTeam
├── LangGraph
├── AutoGen
├── CrewAI
├── openJiuwen
├── MetaGPT
├── ...
```

这会直接把工作量搞爆。

应该是：

```Plain Text
                   EvoTeam Core
                        │
                        ▼
                Agent Runtime Interface
                        │
           ┌────────────┼────────────┐
           │            │            │
           ▼            ▼            ▼
     OpenJiuwen      LangGraph     AutoGen
       Adapter        Adapter       Adapter
          ✅            🔮            🔮
       比赛实现         Future        Future
```

比赛阶段只做：

```Plain Text
OpenJiuwenAdapter
```

其他的是架构扩展点。

---

# 例如代码层面可以这样

以后我们仓库可能长这样：

```Plain Text
jiuwen-evoteam/
│
├── evoteam/
│   │
│   ├── core/
│   │   ├── task.py
│   │   ├── agent.py
│   │   ├── team.py
│   │   ├── strategy.py
│   │   └── evolution.py
│   │
│   ├── evolution/
│   │   ├── prompt_optimizer.py
│   │   ├── tool_optimizer.py
│   │   ├── team_optimizer.py
│   │   └── evaluator.py
│   │
│   ├── runtime/
│   │   ├── base.py
│   │   │
│   │   └── openjiuwen/
│   │       ├── adapter.py
│   │       ├── agents.py
│   │       ├── workflow.py
│   │       └── tools.py
│   │
│   ├── memory/
│   │   ├── trajectory.py
│   │   ├── experience.py
│   │   └── strategy_memory.py
│   │
│   └── evaluation/
│
├── server/
│   └── FastAPI
│
├── web/
│   └── React / Vue
│
├── experiments/
│   ├── report_generation/
│   ├── data_analysis/
│   └── task_planning/
│
└── tests/
```

这里有一个非常关键的小设计。

例如：

```Python
class AgentRuntime:
    async def create_agent(...):
        ...

    async def run_agent(...):
        ...

    async def run_team(...):
        ...
```

然后：

```Python
class OpenJiuwenRuntime(AgentRuntime):
    ...
```

**只有这一层直接 import `openjiuwen`。**

我们的：

```Plain Text
Evolution Engine
Evaluator
Team Planner
Strategy Memory
```

都不知道底下到底是什么框架。

这就是所谓的：

> **核心逻辑解耦，基础能力依赖 openJiuwen。**

---

# 那这样会不会被评委说“不够基于 openJiuwen”？

只要我们做对，不会。

因为题目的原话确实明确要求“基于 openJiuwen 构建”，并把动态 Agent 角色、协作和历史驱动演进作为核心。(AtomGit AI社区)

我们的执行链完全可以是：

```Plain Text
EvoTeam
    ↓
OpenJiuwen Agent Core
    ↓
ReActAgent / WorkflowAgent
    ↓
Model + Tool
```

而且 README 里明确写：

> EvoTeam is a self-evolving multi-agent system built on the openJiuwen Agent Framework.

答辩架构图上：

```Plain Text
Application Layer
────────────────────────
EvoTeam Web

Evolution Layer ⭐ 我们
────────────────────────
Organization Evolution
Strategy Evolution
Prompt Evolution
Evaluation

Agent Orchestration Layer ⭐ 我们 + 九问
────────────────────────
Dynamic Team Orchestrator

openJiuwen Framework
────────────────────────
ReActAgent
WorkflowAgent
Tool
Model
Memory
Runtime

Infrastructure
────────────────────────
LLM / Search / Python / DB
```

这样评委一看就懂：

> openJiuwen 是基础设施，我们在它上面做了一层新的 Multi-Agent Evolution System。

---

# 那九问 Studio 完全不用了吗？

**V1 可以完全不用。**

但我建议在后期加一个：

> **OpenJiuwen Studio Integration**

作为 bonus。

例如：

```Plain Text
openJiuwen Studio
        │
        │ REST / MCP
        ▼
     EvoTeam
        │
        ▼
Evolution Engine
```

官方 Studio 当前本身就有插件管理，并且其开发版本列出了 MCP 支持和 REST API，因此未来做这种集成路径是合理的。(GitCode)

这样答辩的时候可以说：

> EvoTeam 既拥有独立 Web 控制台，也可以作为能力服务接入 openJiuwen 生态。

这就很好听。

不过我强调：

**这属于锦上添花，不是第一阶段目标。**

---

# Web 页面为什么一定建议自己做？

因为这道题明确说：

> 鼓励展示 Agent 协作过程，可视化加分。([AtomGit AI社区](https://competition.gitcode.com/competition/guochuang-2026/u-j1))

所以我们的 UI 不是简单搞个 ChatGPT 聊天框。

而应该专门为“自演进”服务。

比如页面：

```Plain Text
┌─────────────────────────────────────────────────────┐
│ EvoTeam                         Generation 7         │
├─────────────────┬───────────────────────────────────┤
│                 │                                   │
│   Agent Graph   │            Chat / Task            │
│                 │                                   │
│    Planner      │  分析 sales.csv 销量下降原因       │
│      │          │                                   │
│   ┌──┴──┐       │                                   │
│ Analyst Coder   │                                   │
│   │       │     │                                   │
│   └───┬───┘     │                                   │
│     Critic      │                                   │
│                 │                                   │
├─────────────────┴───────────────────────────────────┤
│ Execution Timeline                                  │
│ Planner → Analyst → Code → Critic                   │
├─────────────────────────────────────────────────────┤
│ Evolution                                           │
│                                                     │
│ ⚠ Numerical errors detected: 4                     │
│ + Spawned CodeVerifier                              │
│ Analyst Prompt v2 → v3                              │
│ Score: 0.74 → 0.86                                  │
│ Cost: 1.00 → 0.92                                   │
├─────────────────────────────────────────────────────┤
│ Evolution History                                   │
│ Gen 1 → Gen 2 → Gen 3 → ... → Gen 7               │
└─────────────────────────────────────────────────────┘
```

这东西九问 Studio 不一定天然围绕我们的比赛故事设计。

**自己做，展示效果会好非常多。**

---

# Runtime 要不要一开始就上？

也不要。

官方本身把 `agent-runtime` 定位为 Agent 服务化运行、会话和生命周期管理这一层。([GitCode](https://gitcode.com/openJiuwen?utm_source=chatgpt.com))

我们开发阶段：

```Plain Text
FastAPI
  ↓
EvoTeam
  ↓
openJiuwen agent-core
```

完全够。

等 MVP 跑通以后，如果我们需要表现：

- 分布式
- 多会话
- Agent 服务化
- 大规模并行

再考虑：

```Plain Text
EvoTeam
 ↓
openJiuwen Runtime
```

不要第一周就把自己埋进基础设施里面。

---

# 所以现在我给你的最终路线

可以压缩成一句：

> **我们不是给 openJiuwen Studio 写一个插件，也不是重新造一个 openJiuwen，而是基于 openJiuwen Python Agent SDK 构建一个独立的“自演进多智能体组织平台 EvoTeam”。**

架构上：

```Plain Text
                        EvoTeam
                           │
                ┌──────────┴──────────┐
                │                     │
             Web UI             Evolution Engine
                                      │
                                Team Orchestrator
                                      │
                             Agent Runtime Interface
                                      │
                                      ▼
                           OpenJiuwen Adapter
                                      │
                                      ▼
                         openJiuwen agent-core
                                      │
                      ┌───────────────┼──────────────┐
                      ▼               ▼              ▼
                    Model           Tools          Memory
```

同时保留：

```Plain Text
未来
Agent Runtime Interface
├── OpenJiuwen ✅
├── LangGraph   Future
├── AutoGen     Future
└── ...
```

但**不要真的现在去实现后面三个。**

这也方便我们后面包装项目定位：

> **EvoTeam 是一个以 openJiuwen 为核心运行底座、面向动态多智能体组织与持续自演进的协作平台。其演进逻辑与底层 Agent Runtime 解耦，并具备向其他 Agent 框架扩展的能力。**

我觉得这个定位比“openJiuwen 插件”高一个层次，也比“我们做一个什么都支持的通用 Agent 平台”务实得多。

\*\*下一步就可以真正落代码架构了。\*\*我建议下一轮直接定 `jiuwen-evoteam` 仓库的 **技术栈 + 模块划分 + 第一阶段 MVP + 第一个最小可运行的 Planner/Executor/Critic Demo**，这样我们就可以开始写第一批代码，而不是继续停留在概念阶段。