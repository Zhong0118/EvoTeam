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

运行过程采用 **“主会话 → Agent 行 → Child Session”三级信息密度**。

核心目标：

> 用户默认看到的是任务推进；需要解释时，可以逐层进入某个 Agent 自己的完整执行过程。

## Level 1：主会话摘要

正在运行时，主会话只展示角色、当前任务与状态：

```text
◇ Planner
  已完成任务拆解

◇ Researcher A
  调研 Agent Harness                         ● Running

◇ Researcher B
  调研 Context Engineering                   ✓ Completed

◇ Analyst
  等待两个 Researcher                        ○ Queued
```

Turn 完成后自动折叠为：

```text
5 个 Agent · 11 次工具调用 · 6 次协作消息 · 3 个产物       ⌄
────────────────────────────────────────────────────────────

最终回答……
```

这保证：

```text
Final Answer > Process
```

## Level 2：展开某个 Agent 的过程

点击 `Researcher A` 后，在当前 Transcript 中展开它自己的运行过程：

```text
◇ Researcher A
  调研 Agent Harness                               ✓ 7.2s

  思考
  需要先理解 Harness 的 Conversation Shell 与 Trace 投影……

  搜索
  deepseek harness architecture

  读取
  packages/client/ui-conversation/README.zh.md

  读取
  packages/client/ui-trajectory/README.zh.md

  搜索
  subagent delegation

  思考
  Harness 将 Chat 与 Trajectory 作为同一 Session 的不同 View……

  生成产物
  harness_notes.md

  发送
  Researcher A → Analyst
  harness_notes + references

  6 次工具调用 · 6.2k tokens
```

Agent 内部允许展示：

```text
reasoning
tool_call
tool_result
artifact
message
retry
output
```

这里仍然使用 Coding Agent 式连续 Transcript，不使用大块 Dashboard Card。

## Level 3：完整 Agent Run

当用户点击“查看完整运行”时，打开该 Agent 的详细运行视图 / Inspector：

```text
Researcher A

过程 | 消息 | 产物 | 上下文
────────────────────────────

01 reasoning
02 search
03 read
04 read
05 reasoning
06 artifact
07 message → Analyst
```

完整视图可查看：

- Input / Output
- Tool Args / Tool Result
- Agent ↔ Agent Message
- Artifact
- Context Snapshot
- Token / Latency
- caused_by / parent delegation
- Retry / Error

因此每一个小 Agent 都不是一个简单节点，而是一个可以被观察的 **Child Session / AgentRun**。

# 8. Chat 中的 Agent 表达

Agent 是主会话中的 **过程 metadata + 可展开 Child Session**，不是大卡片。

建议默认行结构：

```text
◇ Researcher A
  Harness / Runtime 调研                  ✓ 6 tools

◇ Researcher B
  Context / Compaction 调研               ● Running

◇ Analyst
  综合两个 Researcher 的产物              ○ Queued
```

状态：

```text
○ queued
● running
✓ completed
! failed
↻ retry
```

点击 Agent 行：

1. 第一次点击：在 Chat 中展开该 Agent 的内部过程；
2. 点击“完整运行”：打开右侧 Agent Inspector 或 Child Session；
3. 可以跳到 Team View 中定位同一节点；
4. 可以跳到 Trace 中按同一 `agentRunId` 筛选；
5. 如果该 Agent 发生了演进归因，可以从这里跳到 Evolution 对应 Diff。

重要规则：

```text
同一个 AgentRun
   ↕
Chat 展开
   ↕
Trace 筛选
   ↕
Team 节点
   ↕
Evolution Attribution
```

这四处必须引用同一个运行实体，不允许各自维护一套状态。

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

Trace 是 DSH-style observability view，但在 EvoTeam 中额外支持 **AgentRun 层级与父子委派关系**。

布局：

```text
┌─────────────────────────────────────────────────────────────────────┐
│ 时长   Turn   Tool   Agent        AgentRun ▾                搜索    │
├─────────────────────────────────────────────────────────────────────┤
│ INPUT       ██                                                       │
│ MODEL         █████       ███                                        │
│ AGENT              ███      █████                                    │
│ TOOL                  ███ ███████                                    │
├─────────────────────────────────────────────────────────────────────┤
│ 01 User        task                                                  │
│ 02 Model       reasoning                         2.3s                │
│ 03 Planner     plan                              1.1s                │
│ 04 Delegate    Planner → Researcher A                                │
│ 05 Tool        search                            3.4s                │
│ 06 Tool        read                              1.2s                │
│ 07 ResearcherA artifact:harness_notes            4.9s                │
│ 08 Message     Researcher A → Analyst            0.1s                │
│ 09 Analyst     running                                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Trace 过滤维度

```text
All
AgentRun
Tool
Message
Artifact
Evaluation
Evolution
```

支持：

```text
只看 Researcher A
只看 Planner 的 children
只看 Agent ↔ Agent 消息
只看 retry / failed
```

点击记录打开 Inspector：

```text
Inspector

type
agent_message

agentRunId
researcher_a_run_01

parentAgentRunId
planner_run_01

source
Researcher A

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

## 与其他 View 的联动

点击 AgentRun：

```text
Trace → Team
```

高亮相同 Agent 节点。

点击 Message：

```text
Trace → Team Edge
```

高亮对应数据流。

点击 Artifact：

```text
Trace → Artifact Panel
```

打开相同产物。

因此 Trace 是执行证据的完整时间 / 因果视图，而不是独立的数据页面。

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

## Team 的两个模式

顶部建议提供：

```text
图谱 | 协作流
```

### 图谱

用于展示：

- 动态 Agent Team 结构
- 当前运行节点
- 并行 / 串行关系
- Agent ↔ Agent 数据流
- Retry / Feedback
- 回放

### 协作流

借鉴“Agent Workspace / Slack for Agents”的表达，按时间展示 Agent 之间的工作交接：

```text
Planner
@ResearcherA 调研 Harness UI
@ResearcherB 调研 Context Engineering

Researcher A
已生成 harness_notes
@Analyst 已发送

Researcher B
context_notes 已完成
@Analyst 已发送

Analyst
正在综合两个结果……

Verifier
结论 3 的证据覆盖不足
@ResearcherA 请补充来源
```

默认 Chat 不展示成 Agent 群聊；协作流只存在于 Team View 中，作为图谱之外的第二种观察方式。

## 节点内容

```text
Researcher A

● Running

读取 ui-trajectory/README

6 tools · 6.2k tokens
```

节点下只展示 **当前 step**，避免图过重。

## 节点 Hover

```text
Role
Model
Prompt
Skills
Current Step
Tokens
Latency
Child count
```

## 节点 Click：Agent Inspector

点击节点后打开右侧 Contextual Side Panel：

```text
Researcher A

过程 | 消息 | 产物 | 上下文
────────────────────────────

Timeline

✓ reasoning
✓ search        3.4s
✓ read          1.2s
● read          0.8s...
○ synthesis
○ handoff

────────────────────────────

6 tools
6.2k tokens

[打开完整运行 →]
```

Inspector 的四个 Tab：

```text
过程
消息
产物
上下文
```

### 过程

展示该 AgentRun 内部：

```text
reasoning → tool → result → artifact → handoff
```

### 消息

展示：

```text
Parent → Agent
Agent → Peer
Peer → Agent
Agent → Parent
```

### 产物

展示该 Agent 的：

```text
inputArtifacts
outputArtifacts
```

### 上下文

展示：

```text
context snapshot
token budget
compaction
memory / inherited context
```

点击“打开完整运行”后，可以进入该 Agent 的完整 Child Session，而不是只看一个小弹层。

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
  | { type: "agent-run"; agentRunId: string; tab?: "process" | "messages" | "artifacts" | "context" }
  | { type: "strategy-diff"; target: string }
```

`agent-run` 替代只保存 `nodeId` 的简单 Agent Panel，因为同一角色在一个 Session 中可能多次实例化，也可能递归生成 Child Agent。

Contextual Side Panel 的职责：

```text
Chat        → Artifact / AgentRun
Trace       → Event / AgentRun
Team        → AgentRun
Evolution   → Strategy Diff / Attribution AgentRun
```

同一时刻只允许一个 Side Panel：

```text
Artifact Panel
AgentRun Inspector
Trace Inspector
Strategy Diff Inspector
```

不能同时抢占右侧空间。

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
    agent-run.tsx

  features/

    conversation/
      conversation-view.tsx
      transcript.tsx
      turn.tsx
      process-fold.tsx
      agent-row.tsx
      agent-process.tsx
      child-agent-session.tsx
      tool-row.tsx
      artifact-row.tsx
      composer.tsx

    trajectory/
      trajectory-view.tsx
      timeline-overview.tsx
      event-table.tsx
      event-inspector.tsx
      agent-run-filter.tsx

    team/
      team-view.tsx
      team-graph.tsx
      collaboration-feed.tsx
      agent-node.tsx
      agent-edge.tsx
      graph-playback.tsx
      agent-run-inspector.tsx
      agent-process-tab.tsx
      agent-messages-tab.tsx
      agent-artifacts-tab.tsx
      agent-context-tab.tsx

    evolution/
      evolution-view.tsx
      strategy-graph-diff.tsx
      evolution-trigger.tsx
      evolution-attribution.tsx
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

    runtime/
      agent-run.ts
      agent-event.ts
      projections.ts
```

# 22. 数据源统一原则

核心事件流：

```text
Runtime
   ↓
Session Event Stream
   ↓
AgentRun / AgentEvent
   ↓
Projection / Adapter
   ├─ Chat Projection
   ├─ Trace Projection
   ├─ Team Projection
   ├─ Collaboration Projection
   └─ Evolution Projection
```

不要：

```text
Chat 自己一套数据
Trace 自己请求另一套
Team 再重新拼一次
Agent Inspector 再请求第四套
```

否则会导致 UI 之间无法联动。

## AgentRun 必须是一等实体

每一个小 Agent 都看成一个独立运行实例：

```ts
interface AgentRun {
  agentRunId: string

  sessionId: string
  parentAgentRunId?: string
  delegationId?: string

  role: string
  agentId: string

  status:
    | "queued"
    | "running"
    | "completed"
    | "failed"

  startedAt?: string
  endedAt?: string

  inputArtifacts: string[]
  outputArtifacts: string[]
}
```

这支持：

```text
Main Agent
  └─ SubAgent
      └─ SubSubAgent
```

未来即使出现递归委派，也不需要推翻 UI。

## AgentEvent

Agent 自己内部的事件统一归到 `agentRunId`：

```ts
interface AgentEvent {
  eventId: string

  sessionId: string
  agentRunId: string

  sequence: number

  type:
    | "reasoning"
    | "tool_call"
    | "tool_result"
    | "message"
    | "artifact"
    | "retry"
    | "output"

  sourceAgentRunId?: string
  targetAgentRunId?: string

  causedBy?: string[]
  payload: unknown
}
```

关键字段：

```text
agentRunId
parentAgentRunId
sourceAgentRunId
targetAgentRunId
```

它们分别支撑：

```text
Agent 自己做了什么
谁创建了它
谁给它发消息
它把结果交给谁
```

# 23. 首版数据适配

当前后端不需要为了 UI 一次性重写。

可以继续使用现有：

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

前端增加运行时 Projection：

```text
session
turn
agentRun
agentEvent
processItem
artifact
collaborationItem
```

首版映射建议：

```text
instance
   ↓
AgentRun

event + output + tool call
   ↓
AgentEvent

message
   ↓
AgentEvent(type = message)

node / edge
   ↓
Team Projection
```

如果现有数据里没有稳定 `agentRunId`，短期可以由：

```text
run_id + instance_id
```

组合成前端稳定 ID。

长期后端应直接提供：

```text
GET /sessions/:sessionId/agent-runs
GET /agent-runs/:agentRunId/events
GET /sessions/:sessionId/timeline
```

实时状态通过一个统一流推送：

```text
GET /sessions/:sessionId/stream
```

推荐 SSE。

UI 接到一条事件后：

```text
AgentEvent
   ├─ 更新 Chat AgentProcess
   ├─ 更新 Trace
   ├─ 更新 Team Node / Edge
   ├─ 更新 Collaboration Feed
   └─ 更新 Evolution evidence
```

不要求第一版马上重构全部后端，但数据模型必须朝这个方向收敛。

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
Agent Row
Agent 内部过程展开
Chat / Trace / Team / Evolution Tabs
```

P1：

```text
AgentRun 数据模型 / Frontend Projection
AgentRun Inspector
Artifact Panel
Team Graph
Trace AgentRun Filter
Trace Inspector
Evolution Graph Diff
```

P2：

```text
Team 协作流
SSE 实时 AgentEvent
Team Replay
Artifact Auto Preview
Agent Child Session
Context View
Queue / Steer
```

比赛演示版本至少要完成：

```text
主会话看到多 Agent 执行
↓
点击某 Agent 能看到它自己的过程
↓
Team 图能定位同一个 AgentRun
↓
Trace 能筛选同一个 AgentRun
↓
Evolution 能归因到同一个 Agent / Strategy 变化
```

这条链路比堆更多静态指标更重要。

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

---

# 28. 开源 UI 与参考实现技术路线

这一版不建议从零实现所有控件，也不建议直接复制某一个产品。

采用：

```text
DSH 的产品与执行投影思想
+
Magentic-UI 的多 Agent / Human-in-the-loop UX
+
OpenAgents 的协作流表达
+
OpenCode 的 Agent UI / Renderer 思路
+
EvoTeam 自己的 Team + Evolution
```

## DeepSeek Harness

可重点研究：

```text
@deepseek-ai/dsh-client-ui-chat
@deepseek-ai/dsh-client-ui-primitives
ui-conversation
ui-trajectory
subagent
agent-team-profile
```

其 UI primitives 覆盖：

```text
Button
Input
Menu
Pill
Tag
StateDot
DisclosureRow
Tooltip
HoverCard
Toast

MarkdownText
CodeBlock
TerminalBlock
ReadBlock
DiffBlock
SearchBlock
WebBlock
JsonTree
```

值得直接借鉴的是：

```text
Agent 输出 renderer
Process folding
Tool block
Semantic design tokens
Conversation / Trajectory projection
Subagent delegation model
```

DSH 的 Web 样式策略是：

```text
React
CSS Modules
clsx
自建 ui-primitives
semantic tokens
```

不依赖 Tailwind 或通用组件库。

## OpenCode

可重点研究：

```text
@opencode-ai/ui
packages/ui
theme
code / diff renderer
message / session UI
```

其 UI 包是基于 SolidJS 的，因此：

```text
不建议直接作为 EvoTeam React 依赖
```

但可以借：

```text
组件边界
Design tokens
Code renderer
Diff renderer
Theme architecture
```

## Magentic-UI

Magentic-UI 与 EvoTeam 当前技术栈最接近。

其前端方向包括：

```text
React
Vite
Tailwind
Radix UI
shadcn/ui
TanStack Query
Zustand
Lucide
React Markdown
```

EvoTeam 可以重点借鉴：

```text
Agent progress
Plan progress
Human approval
Steer / Take over
Agent-specific status
```

但不照搬 Browser Automation 产品结构。

## OpenAgents

OpenAgents 的核心启发是：

```text
Workspace
Thread
@Agent
Shared Files
Shared Context
Agent ↔ Agent Collaboration
```

适合借到 EvoTeam 的：

```text
Team → 协作流
```

而不是替代默认 Chat。

---

# 29. EvoTeam 推荐前端技术组合

结合当前 EvoTeam 已有 React 19、React Router、Radix、React Flow、Recharts、Tailwind、Zod 等依赖，推荐：

```text
Application Shell
  → 自研，参考 DSH

基础控件
  → Radix + shadcn/ui 风格封装

Styling
  → Tailwind + semantic design tokens

Chat Transcript
  → 自研 Projection
  → 参考 DSH Conversation

Tool / Output Renderer
  → 参考 DSH ui-primitives
  → Shiki / Markdown / Diff

AgentRun
  → EvoTeam 自研

Team Graph
  → React Flow

Collaboration Feed
  → EvoTeam 自研
  → 参考 OpenAgents

Human-in-the-loop
  → 参考 Magentic-UI

Trace
  → 参考 DSH Trajectory

Evolution
  → EvoTeam 自研
```

原则：

> 可以复用成熟开源项目的交互范式、组件结构和实现思路，但 EvoTeam 的 `AgentRun / Team / Evolution` 必须形成自己的产品与数据模型。

---

# 30. 多 Agent 协作页的最终职责

Team 页最终不只是“画一张 Agent 图”。

它应该回答五个问题：

```text
现在有哪些 Agent？
每个 Agent 在干什么？
每个 Agent 自己内部怎么干的？
Agent 之间传了什么？
为什么任务会从一个 Agent 流转到另一个 Agent？
```

因此：

```text
Team
  ├─ 图谱
  ├─ 协作流
  └─ AgentRun Inspector
```

三者缺一不可。

---

# 31. 最终设计原则补充

原有一句话保持：

> Chat 是产品，Artifact 是结果，Trace 是证据，Team 是机制，Evolution 是差异化。

新增一条：

> **每个 Agent 都是一个可观察的 Child Session；多 Agent 图只是 AgentRun 之间关系的一种投影。**

因此产品结构最终是：

```text
Session
  │
  ├─ Conversation
  │    ├─ Main Agent Process
  │    ├─ Child AgentRun A
  │    ├─ Child AgentRun B
  │    └─ Final Answer
  │
  ├─ Artifact
  │
  ├─ Trace
  │    └─ filter by AgentRun
  │
  ├─ Team
  │    ├─ Graph
  │    ├─ Collaboration Feed
  │    └─ AgentRun Inspector
  │
  └─ Evolution
       └─ Attribution → AgentRun / Strategy
```

这是下一版原型和后续正式前端实现需要共同遵守的结构。

