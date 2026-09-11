# EvoTeam 主工作区前端实施设计书 V3
## Conversation-first Workspace + Live Execution Graph + AgentRun + Team + Evolution

> **这是一份给 Coding Agent 直接执行的实施规范，不是概念稿。**
>
> Coding Agent 在实现时不得只依据自己的 UI 经验“自由发挥”。必须先阅读 EvoTeam 当前前端源码，再 WebSearch / GitHub 阅读本文指定的参考实现，最后严格按照本文的布局尺寸、组件职责、视觉继承、交互状态与验收标准实施。
>
> 本版最重要的变化：默认产品页必须首先是成熟的 Coding Agent / General Agent 工作区；Chat 执行过程中，桌面端可以同时打开右侧 Live Execution Graph；每个小 Agent 都是可观察的 `AgentRun / Child Session`；完整 Trace、Team、Evolution 是同一 Session 的高级视图；视觉必须继承 EvoTeam 当前前端，而不是复制 DSH / OpenCode 的颜色。

---

# 0. Coding Agent 使用本设计书的强制流程

## 0.1 不允许直接开始写代码

在修改任何页面前，必须先完成以下三个步骤。

### Step A：读取 EvoTeam 当前代码

必须检查：

```text
frontend/src/styles/theme.css
frontend/src/app/layout.tsx
frontend/src/main.tsx
frontend/src/pages/trace.tsx
frontend/src/pages/run-detail.tsx
frontend/src/pages/evolutions.tsx
frontend/src/components/ui/*
frontend/src/components/evidence/*
frontend/src/data/schema.ts
frontend/src/data/client.ts
frontend/package.json
```

需要先回答：

```text
1. 当前全局颜色 token 是什么？
2. sidebar 当前宽度是多少？
3. topbar 当前高度是多少？
4. 哪些 Button / Sheet / Badge 能直接复用？
5. 哪些 Panel / PageTitle / columns 样式会导致 Dashboard 感？
6. 当前 Run / Node / Edge / Instance / Event 数据能直接映射出哪些 Session 数据？
7. 哪些旧路由必须保留，避免破坏已有演示？
```

### Step B：必须进行参考项目 WebSearch / GitHub 阅读

不能只阅读本文的总结。至少要打开本文第 2 章列出的参考页面与源码，理解实际实现。

### Step C：编码前写实施计划

在 Coding Agent 的计划中必须明确：

```text
- 哪些旧文件保留
- 哪些旧文件修改
- 哪些新文件增加
- 先完成哪个页面
- 数据如何适配
- 哪些交互先做 mock
- 哪些功能依赖后端
- 如何验证 1440×900 / 1920×1080 / 1280×800
```

如果没有完成 A/B/C，不允许直接开始大规模改 CSS。

---

# 1. 当前 EvoTeam 前端：必须继承的基线

## 1.1 当前视觉不是全部推倒重做

现在的问题不是“颜色不好看”，而是页面组织方式仍然是：

```text
证据工作台 / Dashboard / Admin Console
```

目标是：

```text
Agent Workspace
```

因此主要修改 `Information Architecture / Layout / Content hierarchy / Interaction`，但尽量保留 `Color semantics / Font family / Button language / Border language / Badge language / React + Tailwind + Radix + React Flow 技术栈`。

## 1.2 当前主题颜色是唯一默认视觉基线

当前 `frontend/src/styles/theme.css` 已经定义：

```css
--background: #f4f6f8;
--foreground: #243541;
--primary: #326e78;
--border: #e0e6eb;
--muted: #667783;
--surface: #ffffff;
--candidate: #7660a8;
```

新工作区必须继续使用：

```text
Primary / Active        #326e78
Evolution / Candidate   #7660a8
Page Background         #f4f6f8
Surface                 #ffffff
Border                  #e0e6eb
Main Text               #243541
Muted                   #667783
```

V2 设计稿里出现过的蓝色主色 `#356AE6` 废弃。不要为了像 DSH / Claude / OpenCode 而把整个项目换成蓝色。

## 1.3 新增状态色必须从已有 Badge 语义继承

```text
Success:   text #387d66 / bg #edf6f2 / border #d9eade
Failed:    text #a14e45 / bg #fbf0ee / border #efded9
Waiting:   text #88662b / bg #fff8e9 / border #eee1c2
Candidate: text #77629f / bg #f4f0fa / border #e7dff1
```

不要再定义 electric blue / neon green / bright red。

---

# 2. 编码前必须打开的参考页面

> **这一章不是“可选参考”。Coding Agent 必须实际打开源码或网页后再实现。** 如果可以使用 WebSearch，就先搜索当前最新页面；如果可以使用 GitHub connector，则继续打开对应源码。不允许只根据模型记忆实现。

## 2.1 DeepSeek Harness：主 Conversation Shell

必须打开：

```text
https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/client/ui-conversation
https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/client/ui-chat
```

重点理解：

```text
Conversation 为什么是共享 Shell
不同 View 如何注册到 conversation.view
Session 如何作为共享状态
Chat node 如何从 Session Event 投影出来
assistant-step / tool-call 的 running → settled
```

要理解的链路：

```text
Session Event
↓
Conversation Projection
↓
Chat Node
↓
Renderer
```

## 2.2 DeepSeek Harness：Trajectory

必须打开：

```text
https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-trajectory/README.zh.md
```

重点记录：Trajectory 如何读取 Session Projection、如何表达 duration / turn / tool / assistant、如何与 Conversation 共用同一 Session。

## 2.3 DeepSeek Harness：UI primitives

必须打开：

```text
https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-primitives/README.zh.md
```

重点研究：

```text
DisclosureRow
StateDot
Tag
Pill
MarkdownText
CodeBlock
TerminalBlock
ReadBlock
DiffBlock
SearchBlock
WebBlock
JsonTree
```

学习的是：工具调用不是 Dashboard Card，工具结果应该是紧凑、可折叠、可复制的 renderer。

## 2.4 DeepSeek Harness：Web Styling

必须打开：

```text
https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/web-styling.zh.md
```

重点学习 semantic token、低视觉噪声、feature UI 不自己发明颜色、共享 primitive。但不要把 DSH 的颜色 token 搬到 EvoTeam，EvoTeam 的 token 权威是 `frontend/src/styles/theme.css`。

## 2.5 DSH Plan Graph：本轮最重要参考

```text
https://github.com/HR2AY/DSH-Plan-Graph
https://github.com/HR2AY/DSH-Plan-Graph/blob/main/README.zh.md
https://github.com/HR2AY/DSH-Plan-Graph/blob/main/assets/plan-graph-preview.png
https://github.com/HR2AY/DSH-Plan-Graph/blob/main/client.body.js
```

Coding Agent 必须在 `client.body.js` 中搜索：

```text
projectSnapshot
projectToolBlock
projectToolRecord
projectAssistant
buildTurnGraph
layoutGraph
layoutTurnGraph
edgePath
NodeCard
GraphCanvas
DetailPanel
PlanGraphView
PlanGraphDetails
```

必须理解的不是“它用了 SVG”，而是：

```text
Runtime Snapshot
↓
projectSnapshot()
↓
Graph DTO
↓
group / collapse
↓
layout
↓
Graph Render
```

必须借鉴 6 个交互逻辑：

```text
1. Merge into Conversation
2. Group by Turn
3. Follow Latest
4. Locate in Conversation
5. Node Detail
6. Focus / Flash Node
```

EvoTeam 对应升级成：

```text
Group by AgentRun
Group by Turn
Group by Phase
```

## 2.6 OpenCode：Session Workspace 和 Composer

先看官网最新实际界面：

```text
https://opencode.ai
```

WebSearch：

```text
OpenCode session UI
OpenCode prompt input UI
OpenCode desktop agent interface
```

再看源码：

```text
https://github.com/anomalyco/opencode/blob/dev/packages/app/src/pages/session.tsx
https://github.com/anomalyco/opencode/blob/dev/packages/app/src/pages/session/session-panel-width.ts
https://github.com/anomalyco/opencode/blob/dev/packages/app/src/components/prompt-input-v2.tsx
https://github.com/anomalyco/opencode/tree/dev/packages/session-ui
```

重点研究 Session 页面如何切分 Chat 与 Side Panel、Panel 宽度如何管理、Composer 的模型选择 / 附件 / 引用 / history / queue / abort / submit。不要只做一个 textarea + send button。

## 2.7 Magentic-UI

```text
https://github.com/microsoft/magentic-ui
```

WebSearch：

```text
Microsoft Magentic UI agent progress
Magentic UI orchestrator progress
Magentic UI human in the loop
```

学习计划状态、Agent progress、用户中途干预、approve / take over / steer。不要搬 Browser Automation 产品结构。

## 2.8 OpenAgents

```text
https://github.com/openagents-org/openagents
https://openagents.org/workspace
```

WebSearch：

```text
OpenAgents Workspace multi agent collaboration
OpenAgents Slack for agents
```

只学习 Agent ↔ Agent collaboration feed、@agent、共享上下文、共享产物、消息交接，用于 Team 的“协作流”。

## 2.9 参考项目职责边界

```text
DSH            → Conversation / Trajectory / Tool Renderer / Projection
DSH Plan Graph → Session Event → Flow Graph / Chat+Graph / Locate / Group / Follow
OpenCode       → Session Workspace / Composer / Split Panel
Magentic-UI    → Agent progress / Human-in-the-loop
OpenAgents     → Collaboration Feed
EvoTeam        → AgentRun / Team / Evolution
```

禁止从 DSH 抄颜色、从 OpenCode 抄整套主题、从 Magentic-UI 抄业务结构、从 OpenAgents 把主 Chat 变群聊。

---

# 3. 最终产品信息架构

```text
打开 EvoTeam
↓
新建 Session
↓
直接输入任务
↓
Chat 中看到 Agent 执行
↓
右侧同时看到 Live Execution Graph
↓
最后得到结果 / Artifact
↓
需要深挖时进入 Trace / Team / Evolution
```

一级产品对象只有 `Session / Task`。Run ID / Evidence / Evolution ID / Strategy ID / Node Config ID 全部退到 Inspector / Advanced / Evidence。

---

# 4. 页面整体布局：必须严格执行

## 4.1 Desktop >= 1280px

```text
Sidebar              206px fixed
Topbar                64px
View Tabs             44px
Content height        calc(100vh - 108px)
Right Live Panel      default 420px / min 340px / max 560px
Chat content max      panel closed 860px / panel open 760px
```

## 4.2 1440×900 参考布局

```text
0                                                                    1440
┌───────────────206───────────────┬─────────────────────────────────────┐
│                                 │ Topbar 64                           │
│                                 ├─────────────────────────────────────┤
│                                 │ View Tabs 44                        │
│                                 ├──────────────────────────┬──────────┤
│                                 │                          │          │
│ Session Sidebar                 │ Chat Column              │ Live     │
│ fixed                           │                          │ Panel    │
│ height: 100vh                   │ transcript               │ 420px    │
│                                 │                          │ graph    │
│                                 │                          │          │
│                                 │     Composer             │          │
└─────────────────────────────────┴──────────────────────────┴──────────┘
```

计算：`1440 - 206 = 1234 workspace`；右栏 420 + divider 1，Chat Column 813；Chat inner max 760，左右剩余约 26px。

## 4.3 Panel 关闭

```text
┌────206────┬───────────────────────────────────────────────────────────┐
│ Sidebar   │                        Chat                               │
│           │              max-width: 860px                             │
│           │                    Composer                               │
└───────────┴───────────────────────────────────────────────────────────┘
```

Conversation 不允许拉满 1200px。

## 4.4 Scroll ownership

```text
Sidebar Session List → 自己滚动
Chat Transcript       → 自己滚动
Right Panel           → 自己滚动
Trace Graph           → 自己 pan / zoom
Body                  → 不滚动
```

桌面主工作区 `height:100vh; overflow:hidden;`。新 Workspace 不得继续继承后台页全局 `main { padding: 35px 32px 60px; ... }`，必须使用 scoped layout。

---

# 5. Layout 代码结构

不要继续让所有页面共用当前后台式 Layout。

```text
AppRoutes
  ├─ SessionWorkspaceLayout
  │    └─ /sessions/:sessionId
  └─ LegacyEvidenceLayout
       ├─ /runs
       ├─ /runs/:id
       ├─ /evolutions
       └─ /strategies
```

旧 Dashboard 保留演示 / 调试能力，新 Workspace 不受 PageTitle / footer / main padding 影响。

---

# 6. Session Sidebar：精确布局

## 6.1 固定尺寸

```css
width: 206px;
height: 100vh;
position: fixed;
left: 0;
top: 0;
```

保留 `background:white; border-right:1px solid var(--border)`。

## 6.2 垂直结构

```text
Brand Area                     64px
New Session                    48px region / button 36px
Workspace Label                28px
Current Workspace              42px
Sessions Label                 28px
Session List                   flex:1; overflow-y:auto
divider
Advanced / Evidence            36px
Settings                       36px
bottom                         12px
```

Brand 行：`[mark] EvoTeam [collapse]`，字号 20–22px。New Session 按钮 height 36 / radius 7 / border 1 / bg surface，Hover 沿用当前 `#f1f5f7`。

Session Row：height 40–46 / padding 7px 10px / radius 7。标题 12–13px 单行 ellipsis；副文本 10–11px muted。Active 直接继承当前 `.nav-item.active`：`background:#e9f0f3; color:#275f68`。

主 Sidebar 禁止继续出现“运行记录 / 团队与 Trace / 演进证据 / 版本与指标”作为一级导航；仅保留 New Session / Workspace / Sessions / Advanced Evidence / Settings。

---

# 7. Topbar：精确布局

高度固定 64px，继续沿用当前 topbar 视觉：半透明白背景 + 1px bottom border，无大阴影。

左侧：任务标题 14–16px / weight 600 / max-width 460 / ellipsis。不要继续显示大串后台 Breadcrumb。

右侧：`Strategy v7 / Export / More`。Strategy 是小 Badge，不是大 Button。出现候选时 `Candidate v8` 使用 `--candidate`。

---

# 8. View Tabs：精确布局

Topbar 下固定 44px。

```text
左：对话   轨迹   团队   演进
右：执行图   产物   （仅 Chat View 显示）
```

Tab 不做 Pill。复用当前 filter-tabs 语言：无背景、底部 2px active border、Active `var(--primary)` / 650；Evolution Active 可用 `var(--candidate)`。

---

# 9. Chat View：整个产品最重要的页面

Chat 结构必须是：

```text
ChatColumn
  ├─ TranscriptScroll
  │    └─ ConversationInner
  └─ ComposerDock
```

Chat 本身就是页面，不允许外面再套 Dashboard `Panel`。

ConversationInner：Panel closed max 860；Panel open max 760；左右最小 padding 24，大屏 32。Transcript top padding 28，bottom 150。

## 9.1 User Message

```text
max-width 76%
margin-left auto
background #f1f5f7
border 1px solid #e0e6eb
radius 9px 9px 3px 9px
padding 10px 13px
```

禁止大蓝 Bubble、渐变 Bubble、阴影卡片。

## 9.2 Assistant Message

Assistant 主体不要 Bubble，使用 avatar/name + plain flowing text + markdown + tool/process inline + artifact link。

## 9.3 Agent Process 默认表现

```text
思考
正在拆解任务并选择团队……

◇ Planner
  已完成任务拆解                                      ✓

◇ Researcher A
  调研 Agent Harness                                 ●

◇ Researcher B
  调研 Context Engineering                           ●

◇ Analyst
  等待上游研究结果                                    ○

◇ Verifier
  等待 Analyst                                       ○
```

Agent Row min-height 30 / padding 3px 0，不是 Card。

## 9.4 Agent Row 对齐

```text
18px status icon | 110px role | flex current action | 80px status/duration
```

Running `var(--primary)`；Completed `#387d66`；Queued muted；Failed `#a14e45`；Evolution candidate。

## 9.5 Agent 自身流程必须能展开

点击 Researcher A：

```text
◇ Researcher A
  Harness Runtime 调研                               ✓ 7.2s

    思考
    需要先定位 Conversation 与 Trajectory 的共享数据……

    搜索
    DeepSeek Harness conversation UI

    读取
    ui-conversation/README.zh.md

    读取
    ui-trajectory/README.zh.md

    思考
    二者共享 Session Projection……

    生成产物
    harness-notes.md

    发送
    → Analyst

    6 tools · 6.2k tokens
```

Agent internal process left indent 26px，内部 Step min-height 28。

## 9.6 Tool Row

默认只显示紧凑行：

```text
⌕ Search     DeepSeek Harness Conversation Shell        ✓
```

点击才展开 Query / Result / Duration。不要每个 Tool Call 一个 200px 高 Card。

## 9.7 Turn 完成后折叠

```text
✓ 已完成
5 Agents · 11 tools · 6 handoffs · 3 artifacts         ›
─────────────────────────────────────────────────────────
最终回答……
```

优先级始终是 `Final Answer > Agent Process > Raw Tool Detail`。

## 9.8 三级信息密度

```text
Level 1: Researcher A / Harness 调研 / 6 tools
Level 2: reasoning / search / read / artifact / handoff
Level 3: 完整 AgentRun Inspector
```

---

# 10. Composer：必须像真正 Agent 产品

Composer 不属于 Transcript scroll，使用 `grid-template-rows:minmax(0,1fr) auto`。Wrapper padding `0 24px 18px`，顶部用轻微 transparent→surface gradient。

宽度和 Conversation 对齐：关闭 860，split 760。

外观：border `#d6dfe5` / radius 10 / bg white / shadow `0 5px 18px rgba(36,53,65,.06)`；不要 16–24px 大圆角或粗阴影。

内部：Context Chips → textarea/contenteditable → bottom bar。

```text
@ README.md   @ openJiuwen   2 files

输入任务……

+   Auto ▾   权限 ▾   @上下文               model ▾     ↑
```

输入区 min-height 54 / max-height 180 / line-height 22；超过后内部滚动。

P0：附件、模型、权限、发送、停止、@文件/knowledge。P1：queue、steer、slash command、prompt history。

快捷键：Enter Send；Shift+Enter newline；Esc close popup；运行时空输入 Send 变 Stop；运行时已有新输入可 Queue（后端未支持则明确 disabled，不伪装）。

---

# 11. Chat + Live Execution Graph：本版关键设计

V3 不再让 Chat 和 Trace 完全分离。默认 Chat 在桌面执行期间可同时打开右侧 Live Execution Graph，直接参考 DSH Plan Graph “并入对话界面”。

## 11.1 打开规则

新 Session 未执行：Right Panel closed。

首个 runtime event（task_created / team_created / agent_started）到来时，如果 viewport >=1280 且用户没有在当前 Session 手动禁用，则自动打开 Live Execution Graph。

用户手动关闭后，本 Session 本轮运行不自动再次打开；新 Session 可以重新按默认规则打开。

## 11.2 Right Panel 尺寸

```text
default 420px
min 340px
max 560px
divider 1px
```

支持拖拽。Hit area 4px，visible border 1px。

## 11.3 Header

44px：`执行图 | 产物                               ×`。这是 Chat 内二级切换，不与主 View Tab 混层。

## 11.4 Compact Execution Graph 内容

窄面板默认不展示所有 Tool 节点，只显示 AgentRun 级别：

```text
User Task
↓
Planner
↓
Researcher A       Researcher B
↓                   ↓
Analyst
↓
Verifier
```

Agent Node：Role / Current Step / Status，例如 `Researcher A / ● Running / read ui-conversation`。

Compact Node：width 184 / height 62–72 / radius 7 / border 1 / left stripe 3px。

Stripe：Active primary；Completed success；Waiting warning；Failed fail；Evolution candidate。

Agent 折叠时显示 `6 tools · 2 artifacts`。点击展开后才出现 thinking→search→read→artifact→handoff。

## 11.5 Toolbar

只保留 icon + tooltip：Follow Latest / Group / Hide Tools / Fullscreen。不要一排 8 个文字 Button。

## 11.6 Follow Latest

运行中默认 ON。新 active node 出现自动定位。用户 pan / zoom / select historical node 后暂停 follow，显示“跟踪最新”恢复按钮。

## 11.7 Chat ↔ Graph 双向定位

所有执行元素必须有稳定 ID：

```text
data-flow-key = event:<eventId>
data-flow-key = agent-run:<agentRunId>
data-flow-key = tool:<callId>
data-flow-key = message:<messageId>
data-flow-key = artifact:<artifactId>
```

Chat 点击 Agent → Graph 定位；Graph 点击 Tool → Chat scroll 到对应 Tool Row。禁止依靠 index / DOM order / 显示文本定位。

## 11.8 技术实现

不要复制 DSH Plan Graph 的手写 SVG canvas。EvoTeam 已有 `@xyflow/react`，只参考它的 Projection / Group / Locate / Follow Latest。

```text
AgentEvent
↓
projectExecutionGraph()
↓
ReactFlow Nodes / Edges
↓
ReactFlow
```

建议 minZoom .45 / maxZoom 1.40 / fitViewPadding .18 / Background gap 20 color border。Controls 放右下，小尺寸。

---

# 12. Artifact Panel

同一个 Right Panel 的第二种内容，Graph 与 Artifact 不同时占右侧。

```ts
type ChatSidePanel =
  | "none"
  | "execution"
  | "artifact"
  | "agent-run"
  | "event-detail"
```

Artifact 支持 Code / Diff / File / Report / Sources / Table / Chart / Slides / Plan。Chat 中只显示紧凑 artifact row，如 `▤ evoteam-architecture.md / 12 sources / Markdown`，点击后右栏切换 Artifact。

---

# 13. 完整 Trace View

进入“轨迹”后使用完整 Workspace 区域，不再使用 Chat 的 760px 阅读宽度。

内部两个模式：`流程图 | 时间线`，默认流程图。

流程图 Toolbar：Group AgentRun/Turn/None、Hide Tools、Only Errors、Follow Latest、Search。

默认 Group by AgentRun：

```text
User Task
   │
   ▼
Planner (4 steps)
   │
   ├────────────────────┐
   ▼                    ▼
Researcher A         Researcher B
8 steps              7 steps
   │                    │
   └──────────┬─────────┘
              ▼
           Analyst
           6 steps
              │
              ▼
           Verifier
```

展开 AgentRun 后显示 reasoning / tool / artifact / message 等内部节点。

统一 Graph Node Type：TASK / AGENT / THINK / TOOL / MESSAGE / ARTIFACT / VERIFY / ERROR / EVOLUTION。不要把后端几十种 event_type 直接作为 UI 类型。

Tool 分类参考 DSH Plan Graph：read/search/list→inspect；bash/python/workflow→execute；test/lint/check/verify→verify；wait→wait；other→tool。

Trace 时间线模式：上方 INPUT/MODEL/AGENT/TOOL/MESSAGE overview，下方事件表，列为 # / Type / Owner / Summary / Duration / Tokens。

选中节点时右侧 Inspector 默认 360px，允许 340–400；无 selection 时关闭。

---

# 14. Team View

Team 顶部提供 `组织图 | 执行流 | 协作流`，三者不要混到一张图。

组织图只展示 AgentRun / Role。Agent Node width 190 / min-height 82，内容只放 role、name、current step、tools/tokens，不显示 Prompt 全文、Config ID、Raw JSON。

点击 Agent 打开右侧 AgentRun Inspector：`过程 | 消息 | 产物 | 上下文`。

过程复用 AgentProcess；消息显示 Parent→Agent / Agent→Peer / Peer→Agent / Agent→Parent；产物显示 input/output artifacts；上下文展示 inherited context / token budget / compaction / memory / prompt version / model / skills / tool policy，Raw JSON 放最底折叠。

“执行流”复用 TraceExecutionGraph，默认按 AgentRun 分组，不实现第二套图引擎。

“协作流”参考 OpenAgents：按时间显示 @Agent、artifact handoff、补充请求等。它不是普通用户 Chat，只存在于 Team 页面。

---

# 15. Team 数据流动画

只在真实 handoff 发生时动画，例如 `Researcher A ──●────► Analyst / artifact`。禁止所有 Edge 永久流光、所有节点永久 pulse、背景粒子。

Edge：normal solid；conditional dashed；retry/feedback warning；evolution diff candidate。

---

# 16. Evolution View

Evolution 不做 Dashboard。页面只回答：为什么变、变哪里、效果如何、是否晋级。

第一屏：Trigger + Current Strategy vs Candidate Strategy。主内容 max 1200，Current/Candidate `1fr | 48px | 1fr`，Graph height 320–400。Changed Node 只使用 `var(--candidate)`。

Graph 下方依次 Trigger → Attribution → Patch → Validation → Gate Decision。Validation 用紧凑 table，不要 6 个 KPI Card。

---

# 17. 视觉系统：强制匹配已有项目

禁止在新 Workspace 里重定义整套颜色；优先 `var(--background/foreground/primary/border/muted/surface/candidate)`。

允许新增尺寸 token：

```css
:root {
  --workspace-sidebar-width: 206px;
  --workspace-topbar-height: 64px;
  --workspace-tabs-height: 44px;
  --workspace-chat-max: 860px;
  --workspace-chat-max-split: 760px;
  --workspace-side-default: 420px;
  --workspace-side-min: 340px;
  --workspace-side-max: 560px;
}
```

圆角：button 6–7 / session row 7–8 / composer 10 / node 7–9 / side panel 0。Shadow 默认无，仅 Composer / Hover Node / Popover 轻微使用。

字体继续 `-apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, sans-serif`；代码 `ui-monospace/SFMono/Menlo`。Session title 15–16；body 13–14；Agent 12；Tool 12；Metadata 10–11；Badge 10。主 Workspace 不要 28px H1。

---

# 18. 动效规范

普通 transition 120–180ms。Running 只允许小 Status Dot pulse。Handoff edge packet 500–900ms，结束消失。Locate 时 center node + border flash 两次，参考 DSH Plan Graph。

---

# 19. 数据模型

```ts
interface AgentRun {
  agentRunId: string
  sessionId: string
  parentAgentRunId?: string
  delegationId?: string
  nodeId?: string
  instanceId?: string
  role: string
  agentId: string
  status: "queued" | "running" | "completed" | "failed"
  startedAt?: string
  endedAt?: string
  inputArtifacts: string[]
  outputArtifacts: string[]
}

interface AgentEvent {
  eventId: string
  sessionId: string
  agentRunId?: string
  sequence: number
  type:
    | "reasoning"
    | "agent_started"
    | "agent_completed"
    | "tool_call"
    | "tool_result"
    | "message"
    | "artifact"
    | "retry"
    | "evaluation"
    | "evolution"
    | "output"
  sourceAgentRunId?: string
  targetAgentRunId?: string
  callId?: string
  artifactId?: string
  causedBy?: string[]
  payload: unknown
}
```

短期现有数据映射：`agentRunId = run_id + ':' + instance_id`；无 instance 时临时 `run_id + ':' + node_id`。长期后端应真正生成 agent_run_id。

---

# 20. Projection：前端最核心的一层

参考 DSH Plan Graph 的 `projectSnapshot()`，EvoTeam 单独实现：

```text
projectConversation()
projectExecutionGraph()
projectTrajectory()
projectTeam()
projectCollaboration()
projectEvolution()
```

禁止 TeamGraph / Chat / Trace 各自重新解析 Raw Event。

```ts
interface ExecutionGraphNode {
  id: string
  kind: "task" | "agent" | "thinking" | "tool" | "message" | "artifact" | "verify" | "error" | "evolution"
  status: string
  title: string
  summary?: string
  agentRunId?: string
  eventId?: string
  callId?: string
  artifactId?: string
  durationMs?: number
  turn?: number
  parentId?: string
}

interface ExecutionGraphEdge {
  id: string
  source: string
  target: string
  type: "sequence" | "delegation" | "handoff" | "feedback" | "subcall"
}
```

Group 支持 none / turn / agent-run。Right Compact 默认 agent-run；Full Trace 默认 agent-run，可切 turn / none。

---

# 21. State 管理

首版不需要 Redux。推荐 React Context + useReducer + URL Search Params。

```ts
interface SessionWorkspaceState {
  sessionId: string
  activeView: "chat" | "trace" | "team" | "evolution"
  sidePanel: "none" | "execution" | "artifact" | "agent-run" | "event"
  selectedAgentRunId?: string
  selectedEventId?: string
  selectedArtifactId?: string
  followLatest: boolean
  groupMode: "agent-run" | "turn" | "none"
  manuallyClosedExecutionPanel: boolean
}
```

---

# 22. Chat / Graph 定位注册表

React 中优先维护 `Map<string, HTMLElement>`，提供 `registerFlowElement(key, element)` / `locateFlowElement(key)`。Key 用 event/agent-run/tool/artifact。只有虚拟列表或异步渲染元素尚不存在时，再 requestAnimationFrame 或 MutationObserver fallback。

---

# 23. 实时数据

推荐未来 `GET /sessions/:sessionId/stream` SSE。

事件建议：task.started / team.created / agent.created / agent.started / agent.reasoning / tool.called / tool.result / agent.message / artifact.created / agent.completed / evaluation.completed / evolution.triggered / strategy.proposed / strategy.promoted / run.completed。

一条 Event 到来必须同时更新 Chat / Trace / Execution Graph / Team / Collaboration Feed，不要每个页面独立轮询。

---

# 24. 路由

```text
/ → /sessions
/sessions
/sessions/:sessionId
```

View 放 query：`?view=chat|trace|team|evolution`；Panel：`&panel=execution|artifact|agent-run`；Selection：`&agentRun=...&event=...&artifact=...`。刷新应恢复 view/panel/selection。

旧 `/runs /runs/:runId /runs/:runId/trace /evolutions /evolutions/:id /strategies /strategies/:id` 不直接删，先作为 Advanced / Evidence 页面保留。

---

# 25. 文件级实施建议

修改：`frontend/src/main.tsx`、`frontend/src/styles/theme.css`。新增 `frontend/src/app/session-workspace-layout.tsx` 和 `frontend/src/pages/session-workspace.tsx`。

当前 `layout.tsx` 建议保留为 LegacyEvidenceLayout，不彻底重写，风险最低。

推荐目录：

```text
frontend/src/features/
  session/
    session-sidebar.tsx
    session-header.tsx
    session-tabs.tsx
    session-workspace-store.tsx
  conversation/
    conversation-view.tsx
    transcript.tsx
    turn.tsx
    process-fold.tsx
    agent-row.tsx
    agent-process.tsx
    tool-row.tsx
    message-row.tsx
    artifact-row.tsx
    composer.tsx
  execution/
    execution-panel.tsx
    execution-graph.tsx
    execution-node.tsx
    execution-edge.tsx
    execution-toolbar.tsx
    execution-inspector.tsx
  trajectory/
    trajectory-view.tsx
    trajectory-graph.tsx
    trajectory-timeline.tsx
    event-inspector.tsx
  team/
    team-view.tsx
    team-graph.tsx
    collaboration-feed.tsx
    agent-run-inspector.tsx
  evolution/
    evolution-view.tsx
    strategy-diff-graph.tsx
    evolution-trigger.tsx
    evolution-attribution.tsx
    evolution-patch.tsx
    validation-table.tsx
    gate-decision.tsx
  artifacts/
    artifact-panel.tsx
    artifact-router.tsx
  runtime/
    types.ts
    project-conversation.ts
    project-execution-graph.ts
    project-team.ts
    project-trajectory.ts
    project-evolution.ts
    flow-registry.ts
```

优先复用 `components/ui/button`、`components/ui/sheet`、lucide、React Flow、现有 Badge 色彩语义。主 Chat 禁止使用后台式 PageTitle / Panel / columns / guide-strip / KPI cards。

---

# 26. React Flow 与布局

Live Execution / Full Trace / Team / Evolution Diff 尽量基于同一套 React Flow + custom nodes；数据 Projection 不同。共享 BaseFlowNode / StatusStripe / NodeHeader / NodeSummary / NodeFooter，不要四套 node CSS。

Live Execution 首版参考 DSH Plan Graph 的 BFS depth + layer layout 即可，不必立即引入 ELK。Team <=10 Agent 用简单 DAG layer；未来 20+ Agent / 大量回边再考虑 dagre/elk。

---

# 27. Responsive

```text
>=1440: Sidebar fixed + Chat + Right Panel 420
1280–1439: Sidebar 206 + Panel 380–420；保证 Chat >=620
1024–1279: Right Panel 默认关闭，点击后 overlay min(420,45vw)
768–1023: Sidebar collapse/drawer，Chat full，Panel overlay
<768: Sidebar Drawer，Right Panel full-screen Sheet，Tabs 横向滚动
```

任何时候不要把 Chat 压到 500px 左右。

---

# 28. Empty / Loading / Error / Approval

New Session 中间只放 `EvoTeam / 今天想完成什么？ / Composer`，下方最多三个轻量提示“调研 / 编码 / 分析”，不要 6 个大卡片。

Loading：Chat `● 正在组织团队……`；Right Graph skeleton 或“正在创建执行图”。

Error：Agent 行内 `! Researcher A / Tool failed · click to inspect`，不要整页红屏。

Human-in-loop 参考 Magentic-UI，Chat 内嵌 approval：`将删除临时文件并重新运行测试 [允许一次] [始终允许] [拒绝]`，不是浏览器 alert。

---

# 29. 视觉反模式

只要出现以下情况，就说明又做回 Dashboard：

```text
首页出现 4–8 个 KPI 卡
主 Chat 外面套 Panel Card
每个 Agent 是 200px 高的大卡
每个 Tool Call 一个大 Card
主内容顶部 28px H1 + description
Workspace 页面有 footer
大量 20px+ 圆角
右侧永远显示巨大 Agent Graph
颜色突然 teal → blue
Evolution 紫色到处乱用
Trace 和 Team 各自维护独立数据
```

发现必须重构。

---

# 30. V3 默认 Chat 最终形态

```text
┌──── Sidebar 206 ────┬────────────────────────────────────────────────────────┐
│ EvoTeam             │ 调研 Agent Harness                           Strategy │
│                     ├────────────────────────────────────────────────────────┤
│ + 新会话            │ 对话   轨迹   团队   演进             执行图   产物    │
│                     ├──────────────────────────────────┬─────────────────────┤
│ 工作区              │                                  │ Live Execution      │
│ EvoTeam             │ User                             │                     │
│                     │ 帮我调研……                       │      Planner        │
│ 会话                │                                  │       /    \\       │
│ Harness 调研        │ EvoTeam                          │ Research A  B       │
│ UI 重构             │                                  │       \\    /       │
│ Strategy 验证       │ 思考                             │      Analyst        │
│                     │ 正在拆解任务……                   │         |           │
│                     │                                  │      Verifier       │
│                     │ ◇ Planner            ✓          │ Follow latest       │
│                     │ ◇ Researcher A       ●          │                     │
│                     │   └ search ...                   │                     │
│                     │   └ read ...                     │                     │
│                     │                                  │                     │
│                     │ 最终回答……                       │                     │
│                     │ ┌──────────────────────────────┐ │                     │
│                     │ │ 输入任务……                  │ │                     │
│                     │ │ + Auto 权限 model        ↑ │ │                     │
│                     │ └──────────────────────────────┘ │                     │
└─────────────────────┴──────────────────────────────────┴─────────────────────┘
```

---

# 31. Trace 最终形态

```text
┌────Sidebar────┬──────────────────────────────────────────────────────────────┐
│               │ 对话   轨迹   团队   演进                                  │
│               ├──────────────────────────────────────────────────────────────┤
│               │ 流程图 | 时间线     AgentRun ▾  Hide tools  Follow  Search │
│               ├───────────────────────────────────────┬──────────────────────┤
│               │                                       │ Inspector            │
│               │ Task → Planner → Researcher           │ Researcher A         │
│               │              → search → read          │ completed / 7.2s     │
│               │              → artifact               │ Input / Output       │
│               │                                       │ Artifacts            │
└───────────────┴───────────────────────────────────────┴──────────────────────┘
```

---

# 32. Team 最终形态

```text
┌────Sidebar────┬──────────────────────────────────────────────────────────────┐
│               │ 对话   轨迹   团队   演进                                  │
│               ├──────────────────────────────────────────────────────────────┤
│               │ 组织图 | 执行流 | 协作流                         Replay     │
│               ├───────────────────────────────────────┬──────────────────────┤
│               │                Planner                │ AgentRun Inspector   │
│               │              /        \\              │ Researcher A         │
│               │       Research A     Research B       │ 过程 消息 产物 上下文│
│               │              \\        /              │ ✓ search / ● read   │
│               │                Analyst                │                      │
│               │                   |                   │                      │
│               │                Verifier               │                      │
└───────────────┴───────────────────────────────────────┴──────────────────────┘
```

---

# 33. 实施顺序

Phase 0：研究与截图（当前 EvoTeam / DSH Conversation / DSH Plan Graph / OpenCode Session / OpenCode Composer）。

Phase 1：Session Shell，仅 Sidebar / Topbar / Tabs / Chat Empty / Composer。验收：第一眼已经不像 Dashboard。

Phase 2：Chat Process，User/Assistant/Agent Row/Tool Row/Process Folding/Child Agent expand。验收：只通过 Chat 能看懂系统在做什么。

Phase 3：Live Execution Graph，Right Panel / Resizable / Execution+Artifact / projectExecutionGraph / React Flow / Follow Latest / Chat↔Graph locate。验收：Chat 与图完全同步。

Phase 4：Full Trace，流程图 / 时间线 / Group / Filter / Inspector。

Phase 5：Team，组织图 / 执行流 / 协作流 / AgentRun Inspector。

Phase 6：Evolution，Strategy Diff / Trigger / Attribution / Patch / Validation / Gate。

Phase 7：Realtime，最后接 SSE。真实事件前允许 fixture/mock event stream，但数据结构必须和真实 Projection 相同。

---

# 34. 每个 Phase 完成后必须截图验证

至少验证：1440×900 / 1920×1080 / 1280×800 / 1024×768。

检查 Sidebar 是否过宽、Chat 是否过宽、Composer 是否漂、右栏是否把 Chat 压窄、Tool Row 是否像 Card、Graph 是否过密、颜色是否和旧页面断层。

---

# 35. Definition of Done

陌生用户 10 秒内能回答：在哪里输入任务？现在系统在做什么？有哪些 Agent？某个 Agent 自己做了什么？它们之间传了什么？结果在哪里？为什么发生演进？

视觉必须满足：**看起来属于现在这个 EvoTeam 项目，而不是另一个蓝色模板网站。**

Chat 必须满足：`正文是视觉主体 > Process 是辅助 > Raw Event 是第三层`。

Graph 必须来自真实 Event Projection，不是装饰动画。

Chat / Trace / Team / Execution Panel / Evolution Attribution 必须共享同一 AgentRun / Event identity。

---

# 36. 给 Coding Agent 的最终执行指令

下面可直接作为开发任务 Prompt 的前置约束：

```text
你正在重构 EvoTeam 前端主工作区。

不要把它设计成 Dashboard / Admin Console。
默认页面必须是 Conversation-first Agent Workspace。

开始编码前：

1. 阅读当前仓库：
   frontend/src/styles/theme.css
   frontend/src/app/layout.tsx
   frontend/src/main.tsx
   frontend/src/pages/trace.tsx
   frontend/src/data/schema.ts

2. 使用 WebSearch / GitHub 实际打开并阅读：
   DeepSeek Harness ui-conversation
   DeepSeek Harness ui-chat
   DeepSeek Harness ui-trajectory
   DeepSeek Harness ui-primitives
   HR2AY/DSH-Plan-Graph README + client.body.js + preview
   anomalyco/opencode session.tsx
   anomalyco/opencode prompt-input-v2.tsx
   anomalyco/opencode session-panel-width.ts
   microsoft/magentic-ui
   openagents-org/openagents

3. 不得从参考项目复制颜色。
   EvoTeam 当前 theme.css 是视觉权威：
   primary #326e78
   candidate #7660a8
   background #f4f6f8
   foreground #243541
   border #e0e6eb
   muted #667783
   surface #fff

4. 默认 Desktop Shell：
   sidebar 206px
   topbar 64px
   tabs 44px
   chat max 860px
   split chat max 760px
   right panel default 420px / min 340 / max 560

5. 新 Workspace 不复用后台式 PageTitle / Panel / columns / footer。
   旧 Evidence 页面保留为 Legacy / Advanced。

6. 默认 Chat 执行期间可以同时打开右侧 Live Execution Graph。
   这个交互参考 DSH Plan Graph 的 “Merge into conversation”。

7. 不要复制 DSH Plan Graph 的手写 SVG canvas。
   EvoTeam 已有 @xyflow/react。
   只参考它的 projectSnapshot / grouping / follow-latest / node detail / locate-in-chat / graph projection。

8. 每一个 Agent 都必须是 AgentRun / Child Session。
   Chat 中可以展开它自己的 reasoning/tool/result/artifact/message/output。
   Team / Trace 点击同一 Agent 必须定位到同一个 agentRunId。

9. 先完成 Session Shell → Chat → Composer → Agent Process，
   再完成 Live Graph → Trace → Team → Evolution。

10. 每阶段必须在 1440×900 截图检查。
    如果页面第一眼仍像后台 Dashboard，则不能进入下一阶段。
```

---

# 37. 最终设计判断

EvoTeam 不应该通过“满屏 Agent 图”证明自己是多 Agent。正确体验是：用户先觉得这是一个好用的 Agent；然后发现它正在动态组织多个 Agent；继续点击可以看到每个 Agent 自己的完整过程；进入 Team 能看到组织和协作；进入 Trace 能看到每一步 execution 的时间与因果证据；进入 Evolution 能看到系统如何根据跨任务经验改变自己的组织与策略。

> **Chat 是产品，Artifact 是结果，Trace 是证据，Team 是机制，Evolution 是差异化。**
>
> **Live Execution Graph 是 Chat 的实时解释层，不是另一个 Dashboard；每个 AgentRun 是可展开的 Child Session，图只是同一运行事实的另一种 Projection。**
