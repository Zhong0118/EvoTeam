# EvoTeam 前端重构参考调研：OpenCode / Magentic-UI / OpenAgents（代码级事实）

> 调研方式说明：全程未抓取整页 HTML。所有源码经 raw.githubusercontent.com 纯文本下载到本地后按行精准阅读；GitHub API 仅用于目录/树清单。web_fetch 实际用量 0/10；web_search 尝试 1 次（环境引擎 403，放弃，改用 GitHub API）。源文件副本在 `/tmp/evoteam-research/`。
>
> 注意：OpenCode 前端是 **SolidJS**（`createMemo`/`createEffect`/`Show`），移植到 React 19 时状态层需重写，但常量、clamp 公式、DOM 类名、事件处理逻辑可原样照搬。

---

## 1. OpenCode 右栏（session/chat 面板）宽度管理

来源：
- https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/app/src/pages/session/session-panel-width.ts （19 行，完整读取）
- https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/app/src/pages/session/session-panel-width.test.ts （测试，确认语义）
- https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/app/src/pages/session.tsx （2391 行，读取 468–532、2255–2369）
- https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/app/src/context/layout.tsx （1081 行，读取默认值与 resize setter）
- https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/app/src/utils/persist.ts （grep 确认 localStorage）
- https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/ui/src/components/resize-handle.tsx （102 行，完整读取）

### 1.1 常量与公式

```ts
export const SESSION_PANEL_WIDTH_MIN = 450      // 聊天区最小宽
export const REVIEW_PANE_WIDTH_MIN = 480        // review 面板最小预留（普通 diff）
export const REVIEW_PANE_WIDTH_MIN_SPLIT = 800  // review 面板 split diff 预留

sessionPanelWidthMax({available, split}) =
  Math.max(SESSION_PANEL_WIDTH_MIN, available - (split ? 800 : 480))

clampSessionPanelWidth({width, available, split}) =
  available === undefined ? width              // 首帧未测量：原样渲染持久宽度，避免闪跳
                          : Math.min(width, sessionPanelWidthMax(...))
```

设计意图（文件头注释）：**不限制聊天区占窗口百分比，而是给右侧 review 面板预留固定最小宽**，聊天区吃掉其余全部空间。测试注释标明这是回归修复：旧版把聊天区封顶 45%，导致 review 永远 ≥55%。

### 1.2 运行时接线（session.tsx）

- `panelRowWidth` 用 ResizeObserver 测容器行宽；`available = rowWidth - (newLayout ? 8 : 0)`（减去 flex gap，content-box 已除 padding）。
- `sessionPanelMax`：未测量时兜底 `1000`。
- **clamp 只发生在渲染期，不覆写持久值**（窗口缩小挤压聊天区而非 review；窗口再放大时用户宽度回来）：

```ts
sessionPanelWidth =
  !sidePanelOpen()        ? "100%"
  : resizeOpen            ? `${clampSessionPanelWidth({width: layout.session.width(), available, split})}px`
  : /* 仅文件树 */          `calc(100% - ${layout.fileTree.width()}px)`
```

- 动画：非拖拽时聊天区容器带 `transition-[width] duration-240ms cubic-bezier(0.22,1,0.36,1) will-change-width`，`motion-reduce` 时禁用；拖拽/滚动吸附期间关动画。

### 1.3 ResizeHandle（`@opencode-ai/ui/resize-handle`）

Props：`{ direction: "horizontal"|"vertical", edge?, size, min, max, onResize(size), onCollapse?(), onCollapseChange?(collapsed), collapseThreshold? }`

实现要点：`onMouseDown`（`e.detail>1` 双击忽略）→ 记录 start 坐标与 startSize → document 级 `mousemove/mouseup`；拖动时锁 `body.style.userSelect="none"` 与 `overflow="hidden"`；每帧 `onResize(Math.min(max, Math.max(min, startSize+delta)))`；`collapseThreshold>0 && current<threshold` 时翻 `onCollapseChange(true)`，mouseup 时若 collapsed 调 `onCollapse()`；支持 RTL（`getComputedStyle().direction`）。横向 handle 默认 `edge="end"`。
用法：聊天/review 分隔 `<ResizeHandle direction="horizontal" size={clamped} min={SESSION_PANEL_WIDTH_MIN} max={sessionPanelMax()} onResize={w=>{size.touch(); layout.session.resize(w)}} />`；终端堆叠时另有垂直 handle：`min=100, max=window.innerHeight*0.6, collapseThreshold=50, onCollapse→terminal.close()`。

### 1.4 持久化（context/layout.tsx）

- 默认值：`DEFAULT_SIDEBAR_WIDTH=344`、`DEFAULT_FILE_TREE_WIDTH=200`、`DEFAULT_SESSION_WIDTH=600`、`DEFAULT_TERMINAL_HEIGHT=280`、`fileTree.opened=false`、`review.diffStyle="split"`。
- 写入：`layout.session.resize(width)` → `setStore("session","width",width)`（store 键不存在时整体 set）。
- 载体：`persisted()` 把 store 序列化进 **localStorage**（utils/persist.ts：`localStorageDirect` / `localStorageWithPrefix`，带 LRU 缓存与容量驱逐），键为 `Persist.serverGlobal(scope, "layout", ["layout.v6"])` —— 按 server scope 分组、版本号 `layout.v6`，旧键走 `migrate` 迁移。

---

## 2. OpenCode Composer（prompt input v2）

来源（均完整/按需读取）：
- 应用层接线：https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/app/src/components/prompt-input-v2.tsx （589 行，全读）
- DOM 组件：https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/session-ui/src/v2/components/prompt-input/index.tsx （723 行，读 85–269、672–712）
- 交互状态机：https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/session-ui/src/v2/components/prompt-input/machine.ts （261 行，全读）
- 控制器：https://raw.githubusercontent.com/anomalyco/opencode/dev/packages/session-ui/src/v2/components/prompt-input/interaction.ts （482 行，读 200–244 + grep）

### 2.1 分层

`prompt-input-v2.tsx`（app 层）只做**装配**：controller = `createPromptInputV2Controller({store, state, history, commands, context(建议项), attachments, view:{placeholder, agent, variant, submit}})`；真正的 DOM 在 session-ui 的 `PromptInputV2`。建议项合并顺序：`reference(@名) → agents(非 primary) → mcp resources → recent files(按打开 tab 序)`；slash 命令 = 自定义 command + 内建 command。`stopping = working() && blank()`（会话运行中且输入为空 → 发送键变停止键）。

### 2.2 DOM 结构（form 内自上而下）

```
div (flex-col gap-3)
 └ PromptInputV2Popover            // 建议列表，absolute inset-x-0 -top-2 -translate-y-full
                                    //  max-h-80 overflow-auto rounded-xl shadow-raised
                                    //  command-menu 型内嵌搜索框
 └ form data-component="prompt-input-v2"
     class="relative min-h-[96px] w-full overflow-clip rounded-xl bg-bg-base shadow-raised"
     drag 悬停时: border-dashed info 色 + 全屏 "drop files" 遮罩 (absolute inset-0 z-20)
     ├ PromptInputV2Attachments     // 仅 normal 模式；行式横向滚动条：
     │   div data-slot="prompt-attachments-scroll"
     │     class="flex flex-nowrap gap-2 overflow-x-auto no-scrollbar px-2 pt-2 pb-1"
     │   // 图片附件 + context chips；删除按钮 size-4 圆点 hover 出现；图片 chip max-w-[300px] break-words
     ├ div.relative min-h-[60px]
     │   ├ div role="textbox" aria-multiline contenteditable
     │   │   class="min-h-[60px] max-h-[180px] w-full overflow-y-auto whitespace-pre-wrap
     │   │          px-4 pt-4 pb-2 text-[13px] font-[440] leading-5"   ← 输入区滚动关键值
     │   │   shell 模式加 font-mono；mention 内联节点 contentEditable=false，按类型着色
     │   └ placeholder: pointer-events-none absolute inset-x-0 top-0（value 为空时）
     └ div.flex h-11 items-center px-2                    ← 底部控制条，高 44px
         ├ 左(flex-1 gap-1): AddMenu(attach Mod+U/commands/context/shell)
         │   → Agent 选择(Mod+.) → Model 选择(高28px, max-w-[220px], 弹 ModelSelectorPopover;
         │      免费账户换 DialogSelectModelUnpaid) → Variant 选择(Shift+Mod+D, 选项>1才显示)
         └ 右: PromptInputV2SubmitButton —— IconButton size-7 rounded-md，
             icon = stopping ? "stop" : mode==="shell" ? "arrow-undo-down" : "arrow-up"
             disabled = !stopping && !canSubmit()；点击 stopping→onStop() 否则 onSubmit()
```

### 2.3 键盘行为

- **Enter**：editor `onKeyDown` 先走状态机 `controller.onKeyDown(event)`；未被处理时 `key==="Enter" && !shiftKey && !isComposing` → `preventDefault(); if (event.repeat) return; submit()`。**Shift+Enter 不拦截**，走 contenteditable 原生换行。`isComposing` 守卫防中文输入法误发；`event.repeat` 守卫防按住连发。
- **运行中停止**：`working() && (Escape || Ctrl+G)` → `preventDefault + onStop()`（Ctrl 判定为 `ctrlKey && !metaKey && !altKey && !shiftKey`）。按钮路径用 `stopping`（working 且输入为空）。
- **历史**：无修饰键 `ArrowUp/ArrowDown` 且 `navigateHistory` 成功才 preventDefault；entries 按 mode 分 normal/shell 两套；首次上翻把当前输入存 `savedHistory`，回到底部再恢复；条目可携带 comment metadata（restore 时回灌 review comments）。
- 注册命令：`file.attach = mod+u`、`prompt.mode.shell = mod+shift+x`、`prompt.mode.normal = mod+shift+e`。

### 2.4 交互状态机（machine.ts，纯函数，可直接移植）

State：`{ mode:"normal"|"shell", popover: closed | {type:"context"|"command-inline"|"command-menu", query, activeID?}, drag:"idle"|"active", focus:"editor"|"command-search"|"external", historyIndex:number, savedHistory? }`
Event：`input.changed / commands.open / context.open / popover.query|results|active|close|select / key.down / mode.shell|normal / drag.enter|leave / focus.editor|external / context.active`
输出：`{state, commands[], handled}`，commands 是效果指令（`draft.setText / mention.add / popover.filter / suggestion.select / focus.*`）——典型 Elm 架构，React 里用 `useReducer` 一比一还原即可。

关键转移：
- 输入恰为 `"!"` → 进 shell 模式并清空。
- 光标前匹配 `/(?:^|\s)@([^\s@]*)$/` → context popover（按 query 过滤）；行首 `/^\/(\S*)$/` → command-inline popover。
- 已有内容时 `/` 命令打开 **command-menu**（focus 移到弹层搜索框）；空输入则 command-inline 直接写进 editor。
- popover 打开时：`Tab`/`Enter`(非 composing) 选中 activeID；`ArrowUp/Down` 与 `Ctrl+P/N` 循环移动（取模）；`Esc` 与 `Ctrl+G` 关闭并回焦；结果变化自动把 activeID 归到首项。
- shell 模式下 Esc 或空文本 Backspace 回 normal。
- 建议项选中：command → 改写文本；文件/agent/resource → 插 mention 节点。

---

## 3. Magentic-UI 审批与 Agent 进度渲染

来源（main 分支实际路径，全部本地精准读取）：
- https://raw.githubusercontent.com/microsoft/magentic-ui/main/frontend/src/types/message.ts （338 行，全读）
- .../frontend/src/components/chat/MessageRenderer.tsx （274 行，全读）
- .../frontend/src/components/chat/messages/InputRequestMessage.tsx （319 行，全读）
- .../frontend/src/components/chat/messages/SystemStatusMessage.tsx （58 行，全读）
- .../frontend/src/lib/messages/constants.tsx （291 行，全读）
- .../frontend/src/hooks/useWebSocketManager.tsx （1039 行，读 458–542、970–1019）
- .../frontend/src/components/browser/TakeoverNotice.tsx （51 行，全读）
- 树清单：https://api.github.com/repos/microsoft/magentic-ui/git/trees/main?recursive=1

**路径勘误（如实报告）**：用户给出的 `frontend/react/client/src/components/Dialog/` 在 microsoft/magentic-ui 任何可达历史版本中都不存在（`api.github.com/.../commits?path=...Dialog/Plan.tsx` 返回空列表；v0.0.6、v0.2.1 树中也无该目录；4 个猜测 URL 均 404 后停止）。当前 frontend 为 React + Vite + Tailwind，位于 `frontend/src/`。**v0.x 时代的 "Plan step update" 卡片在当前 main 已被整体移除**：全库 `frontend/src` 内 plan 相关路径为 0（types_message.ts 与 parser 均无 plan kind）。当前进度渲染改由下面三类条目承担。审批按钮也不再是 "allow once / reject / take over" 三态，而是下述新模型。

### 3.1 消息模型：按 `kind` 判别的 union

`ParsedMessageBase = { id, timestamp, source, raw }`；kind 全集（19 个）：
`user | cua-browser | cua-non-browser | screenshot | code-execution | orchestrator-tool | tool-result | final-answer | summary | browser-address(隐藏) | internal(隐藏) | error | system-status | input-request | approval-response(隐藏) | continuation-response(隐藏) | reasoning | file | text`

要点：
- `orchestrator-tool`：`{ tool, toolArgs, toolCallId?, approvalStatus?: 'user'|'auto_session'|'auto_policy' }` —— toolCallId 是为审批追踪新加的，tool_result 按 toolCallId 关联、相邻时在 messageListUtils 里 merge 进同一卡片（`shouldMergeOrchestratorTool`）。
- `input-request`：`{ inputType, content, tool?, toolArgs?, category?, reason? }`（approval 专属字段仅在 `inputType==='approval'` 出现）。
- `approval-response` / `continuation-response` 是**隐藏 marker**，不进聊天流，只用于回看审批卡片是否已决（`isParsedInternalMessage` 把 4 种 kind 过滤）。
- `reasoning.thinkingSeconds` 由与上一条消息的时间戳差推导。

### 3.2 WS 协议（useWebSocketManager.tsx）

服务端 → 客户端 `INPUT_REQUEST`：`{ input_type, content, tool?, tool_args?, category?, reason?, timestamp? }`
处理顺序：① 若 `controlState==='user-pending'` → 确认 agent 已暂停，`setControlState('user')` 开接管 UI；② `input_type==='approval'` 且会话命中 `autoApproveAll || autoApproveTools.includes(tool)` → 直接回 `{type:'approval_response', decision:'approve', source:'auto_session'}` 并置 status='active'，**不弹卡片**；③ `setInputRequest(sessionId,{input_type,content})`（决定下一条用户消息语义为"回答"）+ 非当前会话时发通知；④ 有 content 或是 approval → 以 `metadata:{type:'input_request', input_type, tool, tool_args, category, reason}` 追加为可渲染消息。
客户端 → 服务端：
```ts
{ type:'approval_response', decision:'approve'|'deny', source:'user'|'auto_session' }
{ type:'continuation_response', decision:'continue'|'stop' }
```
发送前乐观置 `inputRequest=null`、status='active'（防 "Waiting for your input" 闪烁），失败回滚 `awaiting_input`。

### 3.3 审批卡片（InputRequestMessage → ApprovalCard）

三变体：`text_input`（HeaderedMessage "Input Request"）、`approval`（ApprovalCard）、`continuation`（Continue/Stop 卡，agent 达到 per-batch max_rounds 时出现）。

ApprovalCard 状态机：`responded: 'approve'|'deny'|null` 本地态 + `persistedDecision`（从消息列表扫描本卡之后第一个 `approval-response`，中间允许跳过 `system-status` 条目）→ `decision = responded ?? persistedDecision`。渲染：
- `decision==='approve'` → **整卡返回 null 消失**；deny/alternative → 卡保留但按钮换成红字结果文案（"You denied the command." / "You suggested an alternative."）。
- 卡体：标题 "Approval Required"（`text-lg font-bold` 状态色）→ 说明文案（bash 与非 bash 两种）→ 命令展示块（`tool==='bash' ? toolArgs.command : "tool(k=v, …)"`，mono/border/rounded 代码块）→ Reason 行 + 提示 → 按钮行 `flex justify-end gap-2`。
- 按钮：**Deny**（variant=destructive, X icon）+ **Approve 分体按钮**（Check icon，右侧 ChevronDown 打开 DropdownMenu：`Always approve {tool} in this session`、`Always approve all tools in this session`，选后 `setAutoApprove(sessionId,{scope:'tool'|'all'})` 并立即 approve）。
- 容器样式：`rounded-xl border p-4 shadow-sm bg-muted`。

ContinuationCard 同构：标题 "Keep going?"，Stop(destructive)/Continue，continue → 卡消失，stop → "You stopped here."。

### 3.4 Agent 进度渲染

- `system-status`：`STATUS_CONFIG: Record<ServerRunStatus,{label,className}>` = `created / active / complete / error / stopped / paused / awaiting_input`，7 态各配色（paused、awaiting_input 同为 waiting 色），HeaderedMessage 渲染，content 为空不渲染。
- 工具进度 = `orchestrator-tool` 行：`getOrchestratorToolLabel(tool, progressive)` 返回 **[进行时, 过去时] 二元组**（如 bash: "Running Bash command"/"Ran Bash command"，delegate_cua: "Using web browser"/"Finished web browsing"；未知工具 fallback `Running/Ran {tool空格化}`）+ `getOrchestratorToolIcon` 六类 Lucide 图标（terminal/file/navigation/search/globe/wrench）。CUA 浏览器动作同理 `TOOL_LABELS` 进行时/过去时对（"Clicking"/"Clicked"），thoughts（将来时=计划）与 screenshot.actionResult（过去时=结果）互补。运行中的最后一条用进行时、完成切过去时。
- 布局：`MessageRenderer` 用 `React.memo`；user 气泡右对齐 `bg-secondary rounded-lg px-4 py-3 pl-16`，附件 FileChip/FolderChip 在气泡下右对齐换行；assistant 左对齐平铺 `min-w-0 pr-16`，无头像无卡片。

### 3.5 Take over（人工接管）

`ControlState`：`agent(默认) → 'user-pending'(点 Take Control，等 WS 确认暂停) → 'user'(已接管)`；INPUT_REQUEST 到达即完成迁移并置 `pendingTakeoverFeedback=true`。
`TakeoverNotice`（仅 expanded 浏览器视图）：`min-h-16 flex gap-3 px-4 py-3`；pending 态显示动画条纹 "Waiting for the agent to stop..."；user 态 `bg-primary/20` + 文案 "You are in control of the browser. The agent is paused and won't observe these actions." + **Release Control** 按钮（destructive, MousePointer2Off icon）。接管期间 ChatInput 换 placeholder（"Briefly describe what you changed in the browser."）并 `suppressTaskControls`（隐藏与接管流冲突的任务控制按钮）。

---

## 4. OpenAgents 协作流（仅 1 页 README）

来源：https://raw.githubusercontent.com/openagents-org/openagents/master/README.md （474 行；main/dev 分支 404，master 为默认分支。仅读此一份，未取协议源码，结构粒度止于 README 所示。）

workspace/thread/@agent 信息结构要点：
- **Workspace**：持久 hub，"like Slack, but for agents"；固定 URL `workspace.openagents.org/<id>`，可分享/回访；所有 agent 不管跑在哪都汇入同一 workspace；共享资源 = threads + files + 一个所有人可见的 browser（截图/点击/表单共享）。
- **Channel/Thread**：会话条目按 channel 组织；每个消息条目归属 (workspace, channel)，@mention（`@agent-name`）是任务路由手段——"Use @mentions to direct tasks, or let agents pick up work on their own"。
- **会话隔离（adapter 层语义）**：每个 `(workspace, agent, channel)` 三元组一条稳定 session（Goose 例：session 名 `oa_<sha256(...)[:16]>`），首条消息创建、后续消息 resume；不同 channel/agent/workspace 互不串上下文；同 channel 换 agent 也隔离。
- **运行控制**：workspace 级 **Stop** 控件取消运行中任务；inactivity 超时（如 `GOOSE_INACTIVITY_TIMEOUT` 默认 900s）防止挂死 wedge 整个 channel；agent 首条 workspace 消息即可能暴露配置错误。
- CLI 侧连接模型：`agn connect <name> <workspace-token>`（agent 以 token 注册进 workspace），daemon 后台常驻。

对 EvoTeam 的映射提示：thread 条目最少需要 `{workspaceId, channelId, authorKind(human|agent), content, mentions[], runState(running|stopped|timeout)}`，且 (agent, channel) 维度携带可 resume 的 session id。README 无法给出线上 JSON schema；若需精确字段，后续应对 `@openagents-org/*` npm 包做一次定向源码阅读。

---

## 5. 可达性与失败清单（如实）

| 项 | 结果 |
|---|---|
| OpenCode session-panel-width.ts | ✅ 200，全读 |
| OpenCode prompt-input-v2.tsx | ✅ 200，全读；DOM/状态机实际在 session-ui 包（已补读） |
| Magentic-UI `frontend/react/client/.../Dialog/` | ❌ 当前 404 且经查从未存在于该 repo 提交史（`commits?path=` 空）；按当前 main 的 `frontend/src/...` 完成调研；Plan.tsx 旧版无法定位（v0.0.6/v0.2.1 树、4 种路径猜测均 404/无记录），判定 plan-step UI 已在新版删除 |
| OpenAgents README | ✅ master 200（main/dev 404） |
| web_search | ⚠️ 环境引擎 403 一次，未重试，全部改走 GitHub API + raw curl |
