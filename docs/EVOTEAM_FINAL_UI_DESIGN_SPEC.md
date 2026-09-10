# EvoTeam 前端最终设计方案
## DSH-style Conversation Shell + Artifact Studio + Multi-Agent / Evolution Views

> 目标：让 EvoTeam 第一眼像一个成熟 Coding Agent / General Agent，而不是多智能体监控后台。
> 多智能体、轨迹、自演进是增强能力，不应压过默认任务体验。

---

# 1. 产品原则

EvoTeam 的默认心智模型：

> 新建会话 → 输入任务 → 系统执行 → 用户得到结果 → 必要时继续追问

用户不需要先理解：

- Run
- Evidence
- Strategy ID
- Evolution ID
- Agent Graph

这些都属于运行时和可观测性概念。

因此产品层级定义为：

```text
EvoTeam
  └─ Workspace
      └─ Session / Task
          ├─ 对话 Chat            ← 默认入口
          ├─ 轨迹 Trace           ← 可观测性
          ├─ 团队 Team            ← EvoTeam 特有
          ├─ 演进 Evolution       ← EvoTeam 核心差异
          └─ Artifact Preview     ← 可选右侧增强层
```

---

# 2. 总体布局

桌面端默认布局：

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ EvoTeam        当前任务标题                           Strategy v7    ···     │
├──────────────┬───────────────────────────────────────────────────────────────┤
│              │ 对话   轨迹   团队   演进                     [产物 ▷]       │
│  + 新会话    ├───────────────────────────────────────────────────────────────┤
│              │                                                               │
│ 工作区       │                                                               │
│  EvoTeam     │                    Conversation                               │
│   ├ 任务 A   │                                                               │
│   ├ 任务 B   │     User                                                      │
│   └ 任务 C   │     帮我调研当前 Agent Harness...                             │
│              │                                                               │
│ 最近任务     │     思考 · 已完成                                             │
│   ...        │     4 Agents · 18 次工具调用 · 6 次协作消息              ⌄    │
│              │                                                               │
│              │     EvoTeam                                                   │
│              │     根据调研结果，我建议……                                    │
│              │                                                               │
│              │                                                               │
│              │   ┌───────────────────────────────────────────────────────┐   │
│              │   │ 继续输入任务……                         模型       ↑   │   │
│              │   └───────────────────────────────────────────────────────┘   │
└──────────────┴───────────────────────────────────────────────────────────────┘
```

默认只显示：

```text
Sidebar + Conversation
```

不默认显示第三栏。

---

# 3. Artifact / Preview 右侧栏

这是从 OpenDesign / Studio 思路吸收的部分。

## 默认行为

新会话：

```text
Artifact Panel = closed
```

只有以下情况打开：

1. 用户主动点击顶部「产物」
2. 用户点击 Chat 中的文件 / 报告 / 图表 / 页面 / PPT 产物
3. 系统刚生成一个明确可预览的主要产物，并允许产品策略自动展开一次

右栏宽度建议：

```text
420px – 48vw
```

支持拖动调整。

## 根据任务自动适配内容

```text
Coding
  → Files / Diff / Preview

Research
  → Sources / Report

Data Analysis
  → Table / Chart

PPT
  → Slides

Document
  → Document Preview

Planning
  → Plan / Timeline
```

Artifact 是“任务结果”，不是 Agent 运行状态。

---

# 4. 左侧 Sidebar

参考 Coding Agent。

结构：

```text
EvoTeam

+ 新会话

工作区
  当前项目 / 当前目录

会话
  调研 Agent Harness             Running
  设计 EvoTeam 架构              Completed
  分析实验数据                    Completed
```

不要再把以下对象放一级菜单：

```text
运行记录
演进证据
版本与指标
```

它们都应进入当前 Session 上下文。

---

# 5. Header

顶部第一行：

```text
任务标题                        Strategy v7    Share / Export / More
```

第二行是 View Tabs：

```text
对话     轨迹     团队     演进
```

高级阶段可增加：

```text
上下文
```

但首版不建议直接放太多 Tab。

---

# 6. Chat 视图

Chat 是产品的主界面。

不要使用 Dashboard Card 风格。

正确形态：

```text
User
帮我调研当前 Agent Harness……

思考
正在理解任务和制定计划……

◇ Planner
  已完成任务拆解

◇ Researcher
  搜索 Agent Harness                     6 次工具调用

◇ Researcher
  搜索 Context Engineering               5 次工具调用

◇ Analyst
  综合上游结果                           正在执行

◇ Verifier
  等待 Analyst

EvoTeam
根据当前资料，我建议……
```

---

# 7. 运行过程的折叠方式

正在执行时展开：

```text
◇ Researcher

  搜索   deepseek harness architecture
  读取   README.md
  读取   ui-conversation
  搜索   context compaction
  消息   → Analyst

  ● Running
```

Turn 完成后自动变为：

```text
4 个 Agent · 18 次工具调用 · 6 次协作消息       ⌄
─────────────────────────────────────────────────

最终回答……
```

用户展开后才看到完整过程。

这保证：

```text
Final Answer > Process
```

---

# 8. Chat 中的 Agent 表达

Agent 是 metadata，不是大卡片。

建议行结构：

```text
◇ Researcher
  检索 8 个来源

◇ Analyst
  综合 Researcher / Planner 的输出

◇ Verifier
  校验结论
```

状态：

```text
○ queued
● running
✓ completed
! failed
↻ retry
```

点击该行：

- 展开当前 Agent 的过程
- 可以跳到 Team View
- 可以跳到 Trace 中对应事件

---

# 9. Composer

Composer 应像 Coding Agent，而不是普通聊天输入框。

```text
┌─────────────────────────────────────────────────────────────┐
│ 输入任务，或继续当前任务……                                  │
│                                                             │
│ +   Agent ▾   权限 ▾   @ 文件/知识            model ▾    ↑ │
└─────────────────────────────────────────────────────────────┘
```

首版建议支持：

```text
+ attachment
mode
permission
model
send / stop
```

运行中：

```text
Stop
Queue
Steer
```

如果后端尚不支持 Queue / Steer，可以首版只实现 Stop。

---

# 10. Trace 视图

Trace 是 DSH-style observability view。

布局：

```text
┌─────────────────────────────────────────────────────────────────────┐
│ 时长   Turn   Tool   Agent                                  搜索    │
├─────────────────────────────────────────────────────────────────────┤
│ INPUT       ██                                                       │
│ MODEL         █████       ███                                        │
│ AGENT              ███      █████                                    │
│ TOOL                  ███ ███████                                    │
├─────────────────────────────────────────────────────────────────────┤
│ 01 User        task                                                  │
│ 02 Model       reasoning                         2.3s                │
│ 03 Planner     plan                              1.1s                │
│ 04 Tool        search                            3.4s                │
│ 05 Researcher  completed                         4.9s                │
│ 06 Message     Researcher → Analyst              0.1s                │
│ 07 Analyst     running                                               │
└─────────────────────────────────────────────────────────────────────┘
```

点击记录打开 Inspector：

```text
Inspector

type
agent_message

source
Researcher

target
Analyst

input
...

output
...

tokens
...

duration
...

caused_by
...
```

---

# 11. Team 视图

Team 是 EvoTeam 最有辨识度的独立页面。

这里才使用完整 React Flow。

```text
                         Planner
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
        Researcher A                Researcher B
        Harness 调研                Context 调研
              │                           │
              └────────────┬──────────────┘
                           ▼
                        Analyst
                           │
                           ▼
                        Verifier
```

## 节点内容

```text
Researcher

● Running

搜索 Harness 架构

3 tools · 8.2k tokens
```

## 节点交互

hover：

```text
Role
Model
Prompt
Skills
Current Step
Tokens
Latency
```

click：

打开 Inspector。

---

# 12. Team 数据流

信息真正发生传递时，才动画。

例如：

```text
Researcher ──────●────────► Analyst
                 artifact
```

消息类型：

```text
task
message
artifact
tool_result
context
feedback
```

边样式：

```text
普通协作       实线
条件路由       虚线
Retry          橙色
Evolution Diff 紫色
```

不要无意义循环动画。

---

# 13. Team 回放

Team View 顶部：

```text
实时      回放

|◀   ◀   ▶   ▶|       18 / 46 Events
```

回放驱动的是：

```text
Event Stream → Graph State
```

不是预定义动画。

Trace 和 Team 使用同一个 Event 数据。

---

# 14. Evolution 视图

Evolution 是核心差异化能力。

布局不做后台记录列表，而做：

```text
为什么变化
↓
哪里发生变化
↓
效果怎么样
↓
是否晋级
```

---

# 15. Evolution Strategy Diff

第一屏：

```text
Current Strategy v6                     Candidate v7

       Planner                              Planner
          │                                    │
          ▼                                    ▼
     Researcher                           Researcher
          │                                    │
          ▼                                    ▼
      Analyst                          ╔══════════════╗
          │                            ║   Analyst    ║
          ▼                            ║   CHANGED    ║
      Verifier                         ╚══════╤═══════╝
                                                │
                                                ▼
                                            Verifier
```

Changed：

```text
紫色描边
```

Added：

```text
紫色 + NEW
```

Removed：

```text
红色虚线
```

---

# 16. Evolution Detail

下面依次：

```text
Trigger
Attribution
Patch
Validation
Gate Decision
```

示例：

```text
Trigger

复杂调研任务连续出现高 Token 使用。


Attribution

Analyst
context_policy
confidence: 0.87


Patch

full_history
    ↓
artifact_first_compaction


Validation

Success       92% → 94%
Tokens        31k → 24k
Latency       18s → 16s


Gate Decision

✓ Promote Candidate v7

Rollback
Strategy v6
```

---

# 17. Artifact 与各 View 的关系

Chat：

```text
Artifact 可选展开
```

Trace：

```text
Artifact 默认关闭
右侧优先给 Inspector
```

Team：

```text
Artifact 不出现
右侧可为 Node Inspector
```

Evolution：

```text
Artifact 不出现
右侧可为 Diff Inspector
```

因此“右栏”不是固定功能，而是：

```text
Contextual Side Panel
```

根据当前 View 决定内容。

---

# 18. Layout 状态

```ts
type MainView =
  | "chat"
  | "trace"
  | "team"
  | "evolution"

type SidePanel =
  | { type: "none" }
  | { type: "artifact"; artifactId: string }
  | { type: "event"; eventId: string }
  | { type: "agent"; nodeId: string }
  | { type: "strategy-diff"; target: string }
```

这样不会出现：

```text
Artifact Panel
Agent Inspector
Trace Inspector
```

三个东西同时抢屏幕。

---

# 19. 路由

推荐：

```text
/
  → latest session / new session

/sessions/:sessionId

/sessions/:sessionId?view=chat

/sessions/:sessionId?view=trace

/sessions/:sessionId?view=team

/sessions/:sessionId?view=evolution
```

内部对象通过 query：

```text
?run=...
?event=...
?agent=...
?artifact=...
?evolution=...
```

---

# 20. 旧页面迁移

现有：

```text
/runs
/runs/:id
/runs/:id/trace
/evolutions
/evolutions/:id
/strategies
```

首版可以保留兼容跳转。

目标：

```text
Run
Evolution
Strategy
```

全部成为 Session 内部资源，而不是一级产品导航。

---

# 21. 推荐组件结构

```text
src/

  app/
    shell.tsx

  pages/
    session.tsx

  features/

    conversation/
      conversation-view.tsx
      transcript.tsx
      turn.tsx
      process-fold.tsx
      agent-row.tsx
      tool-row.tsx
      composer.tsx

    trajectory/
      trajectory-view.tsx
      timeline-overview.tsx
      event-table.tsx
      event-inspector.tsx

    team/
      team-view.tsx
      team-graph.tsx
      agent-node.tsx
      agent-edge.tsx
      graph-playback.tsx
      agent-inspector.tsx

    evolution/
      evolution-view.tsx
      strategy-graph-diff.tsx
      evolution-trigger.tsx
      evolution-patch.tsx
      validation-result.tsx
      gate-decision.tsx

    artifacts/
      artifact-panel.tsx
      artifact-router.tsx
      code-preview.tsx
      report-preview.tsx
      chart-preview.tsx

    sessions/
      session-sidebar.tsx
      session-header.tsx
```

---

# 22. 数据源统一原则

核心事件流：

```text
Runtime
   ↓
Session Event Stream
   ↓
Projection / Adapter
   ├─ Chat Projection
   ├─ Trace Projection
   ├─ Team Projection
   └─ Evolution Projection
```

不要：

```text
Chat 自己一套数据
Trace 自己请求另一套
Team 再重新拼一次
```

这会导致 UI 之间无法联动。

---

# 23. 首版数据适配

可以继续使用当前：

```text
Run
nodes
edges
instances
messages
events
evolution
validation
strategy
```

增加前端 projection：

```text
session
turn
processItem
artifact
```

不要求第一版马上重构全部后端。

---

# 24. 视觉规范

整体：

```text
轻
平
克制
高信息密度
```

不要：

```text
大圆角 Dashboard Card
彩色 KPI 宫格
满屏渐变
持续发光的 Agent 节点
```

建议：

```text
Background   #FFFFFF / #FAFAFA
Sidebar      #F5F5F4
Border       #E7E7E5
Text         #202124
Muted        #777C84
Primary      #356AE6
Evolution    #8B5CF6
Success      #45A66B
Warning      #C58A22
Error        #C94A4A
```

比赛演示建议以亮色为默认，和 DSH / Claude / Codex 风格更接近。

Evolution 的专属语义色只使用紫色。

---

# 25. 最终体验

第一次打开：

> 这是一个成熟的 Agent 工具。

执行任务：

> 它好像在内部使用了多个 Agent。

打开 Team：

> 原来它动态组织了一支 Agent Team。

打开 Trace：

> 整个执行过程都可以追踪。

打开 Evolution：

> 它甚至会根据历史经验改变 Agent 团队与协作策略。

这就是正确的产品叙事顺序。

---

# 26. 首版优先级

P0：

```text
Session Sidebar
Conversation Shell
Composer
Process Folding
Chat / Trace / Team / Evolution Tabs
```

P1：

```text
Artifact Panel
Team Graph
Trace Inspector
Evolution Graph Diff
```

P2：

```text
SSE 实时事件
Team Replay
Artifact Auto Preview
Context View
Queue / Steer
```

---

# 27. 成功标准

默认 Chat 页看起来必须首先像：

```text
Coding Agent / General Agent
```

而不是：

```text
Multi-Agent Dashboard
```

只有用户主动进入 Team / Trace / Evolution 后，
才显示 EvoTeam 的复杂运行时能力。

一句话总结：

> Chat 是产品，Artifact 是结果，Trace 是证据，Team 是机制，Evolution 是差异化。
