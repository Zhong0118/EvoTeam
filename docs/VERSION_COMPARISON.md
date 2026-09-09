# EvoTeam 最初 GitHub 版本与当前版本对比

## 1. 对比基线

“最初 GitHub 版本”以远端仓库 `main` 历史中的第一个提交为准：

```text
commit: f072cebfdd6e19de8f5253f9b8bfd0567cda5b5f
date:   2026-09-03 15:28:16 +08:00
title:  初始化仓库和相关文档
```

该提交共 14 个文件，主要是项目构想、架构草案、实验设计和开发约束。唯一程序入口 `main.py` 只输出：

```text
Hello from evoteam!
```

因此，最初版本不是一个可运行的 Multi-Agent Demo，而是一套比较完整的产品与架构设计材料。当前工作目录尚未建立本地 commit，本文通过远端首个 commit 与当前实际文件、测试及运行记录进行比较；不把后来远端提交的功能错误归入最初版本。

## 2. 总体变化

| 维度 | 最初 GitHub 版本 | 当前版本 |
| --- | --- | --- |
| 项目状态 | 产品、架构和实验设计 | 可运行、可评价、可追溯的初代自演进 Demo |
| 文件规模 | 14 个文件 | 约 140 个当前工作树可见文件 |
| Python 业务模块 | 无 `evoteam/` 包 | 约 60 个 Python 模块 |
| Agent 执行 | 无 | DeepSeek + openJiuwen ReActAgent |
| 多 Agent 协作 | 概念设计 | 受限 3/4 节点 DAG |
| 任务内修复 | 无 | Critic 驱动 Executor 最多返工一次 |
| 任务评价 | 实验设计 | 独立确定性项目计划 Evaluator |
| Trace | 仅提出可观察性原则 | SQLite 事件、消息、来源、用量和封存快照 |
| 跨任务经验 | 仅概念 | Experience 聚合与成功反例 |
| 演进触发 | 仅概念 | repeated_failure Monitor Trigger |
| Candidate | 仅概念 | Prompt 更新和新增 Verifier 两类候选 |
| 候选比较 | 仅实验方案 | Current/Candidate 配对验证及多候选选择 |
| 生命周期 | 仅提出可逆要求 | Candidate、Current、Rejected、Promote/Rollback 等状态操作 |
| 演进证据 | 无 | Attribution、Proposal、Validation、Gate、EvolutionRecord 全量持久化 |
| API/CLI | 无实际业务入口 | init、run、observe、evolve、FastAPI 基础接口 |
| 自动化验证 | 无测试目录 | 85 passed，1 skipped |

## 3. 从“设计文档”到“在线执行闭环”

### 最初版本

最初版本已经提出了正确的方向：openJiuwen 提供 Agent 运行能力，EvoTeam 负责组织、评价与演进；系统应当先可观察、再可评价、最后可逆地演进。但这些内容都是目标架构，没有代码证明数据能够沿链路流动。

### 当前版本

当前版本已经实现：

```text
Task
  → TaskAnalyzer
  → Strategy 快照
  → Orchestrator
  → Planner / Executor / Critic（可选 Verifier）
  → 独立 Evaluator
  → SQLite 原子封存
```

Agent 不直接互调，而是由 Orchestrator 使用结构化 `AgentMessage` 转发。Trace 保存 Agent 输入、输出、上游事件引用、token、延迟、运行状态和评价结果。失败、超时和取消也进入终结记录，不只保存成功案例。

这项改进把最初版本的“可观察性”原则变成了可以查询和复盘的执行证据。

## 4. 从固定链路到受限 DAG 与有界返工

最初版本没有运行时编排实现。当前 Orchestrator 支持两种经过静态校验的结构：

```text
Planner → Executor → Critic

Planner → Executor → Verifier → Critic
                   └──────────→ Critic
```

第二种结构中，Critic 同时收到 Executor 原产物和 Verifier 审查结果。系统会拒绝未知角色、悬空边、重复边、自环、循环、任意条件路由以及超过约束的节点数量。

当前还支持一次任务内返工：Critic 返回 `passed=false` 时，Executor 接收 Planner 结果与结构化 `critic_feedback` 后再执行一次，随后 Verifier/Critic 再审核；不会无界循环。

真实 DeepSeek 回归已经观察到：

```text
Planner → Executor → Critic → Executor → Critic
```

且最终 `retry_count=1`。这证明返工是实际消息与模型调用，不是仅在数据模型中增加一个计数字段。

## 5. 从“演进设想”到可运行的离线闭环

最初版本设计了经验驱动演进，但没有可执行模块。当前链路为：

```text
SealedRun
  → ExperienceAggregator
  → StrategyMonitor
  → EvolutionTrigger
  → Failure Attribution
  → Bounded Mutation
  → Candidate
  → Current/Candidate Validation
  → Improvement Attribution
  → Validation Gate
  → Promote / Reject
```

具体改进包括：

- 普通 Online Run 不直接修改 Strategy，演进通过显式离线入口启动。
- CandidateGenerator 不读取验证集答案。
- Current 与 Candidate 使用相同任务、模型、评价器和预算进行配对验证。
- Validation Run 与 Online Run 按 `RunPurpose` 隔离，不污染 Monitor。
- 一轮可生成多个 Candidate，并为每个候选独立分配版本、验证和裁决。
- 只有 Gate PASS 的候选参与选择，一轮最多晋升一个；其余统一拒绝。
- 候选失败、Gate 拒绝和未晋级版本同样保留证据。

## 6. 当前已经能演进什么

当前自动 Mutation 仍是白名单能力，只能进行两类改变：

1. `UPDATE_PROMPT`：将 Executor 的 Prompt 从 `executor@v0` 替换为登记过的 `executor@v1-resource-check`。
2. `ADD_AGENT_CONFIG`：从固定 Role Pool 增加唯一 Verifier，并接入受限拓扑。

系统不会让模型任意写代码、创造新 Role、创建任意 Tool、扩大权限或生成无界工作流。这比开放式“让 Agent 随便改自己”更适合当前 Demo，因为候选差异可定位、可验证、可拒绝、可回滚。

## 7. 最新真实回归证明了什么

2026-09-09 的最新 DeepSeek 回归包含 6 个 Team Run、21 次真实模型调用和 21,276 tokens，证明：

- 复杂三 Agent 项目规划能够通过确定性硬约束检查。
- Critic 反馈能够触发且只能触发一次 Executor 返工。
- 一个真实失败可以形成 Monitor Trigger。
- 同一轮可以生成 Prompt 与 Verifier 两个候选。
- Verifier Candidate 会真实执行四节点 DAG。
- Critic 能收到 Executor 与 Verifier 两路上游证据。
- 两个候选的归因、提案、验证和 Gate 结果全部进入 SQLite。
- 两个候选均不满足 Gate 时，Current 不会被错误替换。

这次没有证明“自演进一定提升效果”。相反，两个候选均被拒绝：Prompt Candidate 虽更省 token 和延迟，但现有 Gate 尚不承认纯效率收益；Verifier Candidate 增加约 17.50% token，超过限制。这个结果说明治理链路生效，但效果证据仍不足。

## 8. 相比最初版本最重要的实质改进

### 8.1 概念有了可执行语义

Role、AgentConfig、AgentInstance、Team、Strategy、Run 和 EvolutionRecord 不再只是架构图中的名词，而是有 Pydantic 契约、身份检查和持久化行为的独立对象。

### 8.2 “多 Agent”不再只是多个 Prompt 顺序调用

当前系统记录消息发送者、接收者和上游完成事件；支持多上游输入、Verifier 分支和 Critic 反馈返工。因此可以解释某个节点看到了什么，以及结果为何进入下一步。

### 8.3 “自演进”不等于在线改 Prompt

长期变化必须经过 Trigger、归因、白名单 Mutation、隔离验证、Gate 和生命周期。当前版本已经能拒绝没有充分收益的候选，并保留 Current。

### 8.4 结果可以由程序独立检查

项目计划不是靠 Critic 自己宣布成功。Team 外的 ConstraintChecker 会检查工作完整性、工期、依赖、技能、人员重叠、可用时间、预算、截止时间和里程碑。

### 8.5 失败成为正式数据

失败 Run、硬错误、Critic 漏检、候选失败、Gate Reject 都会保留，而不是只展示成功输出。这为后续贡献分析、回归和可解释演进提供了基础。

## 9. 当前待改进事项

### P0：补齐 Gate 的效率型晋级规则

最新实验中，Prompt Candidate 的 token 降低约 2.57%、延迟降低约 33.35%，质量与硬约束没有退化，却因 Gate 只承认质量/成功/硬错误收益而被拒绝。应显式区分质量型和效率型 Candidate，并预注册：

- 最小 token 或延迟收益；
- 最大质量回归；
- 候选目标类型；
- 多样本稳定性与置信条件；
- 平局和继续采样规则。

### P0：扩大并冻结验证数据集

当前打包验证集只有一个简单任务，无法说明泛化。应建立 History、Validation、Final Test 三个隔离分区，优先覆盖 20–50 个项目计划任务：串行、并行、技能不足、资源冲突、预算不足、不可行期限、多里程碑、依赖分支和文字/结构矛盾。

### P0：增加专用 Verifier 证据协议

Verifier 当前复用 `PlanningReview`，只能输出 passed/issues。应增加结构化检查项、被检查字段、计算依据和证据引用，使 Critic 能区分模型意见与确定性验证结果。

### P1：受控 Tool / Skill 演进

当前 Agent 没有 Tool 或 Skill。下一步不宜允许生成并立即执行任意代码，而应先建立 Capability Registry、权限白名单、隔离 Smoke Test 和 Gate，再允许 Candidate 从已审核资产中选择或提出待人工审核的新能力。

优先工具可复用现有检查逻辑：

- Executor：排期与成本计算；
- Verifier/Critic：计划硬约束校验。

### P1：更多 Monitor 信号

当前只有 repeated_failure 真正启用。质量漂移、成本超限、低贡献、分布变化、STABLE/Reopen 和上线后退化 Rollback 仍需完成指标口径及测试。

### P1：贡献分析与消融

目前能做 Failure Attribution 和 Improvement Attribution，但不能证明新增 Verifier 的独立贡献。应比较：

- 有无 Verifier；
- Verifier 直接输出是否改变 Critic 判断；
- 删除某条边是否影响质量；
- Agent 增量成本是否值得。

### P1：实验稳定性与成本治理

当前模型调用存在随机波动，而验证只有单任务、单次重复。应增加重复次数、种子记录、均值/方差、P50/P95 延迟和严格的演进总预算。每个 Candidate 目前都会重新跑一遍 Current，比较公平但成本会线性增长。

### P2：数据库迁移和崩溃恢复

新增演进表后，旧数据库需要显式初始化升级；还没有正式迁移命令。长时间演进在进程中断后的幂等恢复、Trigger 消费状态和部分 Candidate 收尾也需要完善。

### P2：Trace 查询和可视化

SQLite 已有完整数据，但缺少面向用户的 Run 时间线和演进对比页面。应提供按 Run/Evolution 查询的 API，再做可视化，避免直接依赖 SQLite 和 SDK 原始日志。

## 10. 建议的下一阶段验收顺序

1. 修正效率型 Gate，并补对应自动化测试。
2. 扩充独立 Validation Set，进行 5–10 次小规模配对回归。
3. 为 Verifier 增加明确检查证据，测量其实际边际贡献。
4. 建立受控 Tool Registry，再允许 Tool Policy Candidate。
5. 增加成本/贡献 Monitor、STABLE/Reopen 和真实 Rollback 测试。
6. 最后再做 Trace API 与展示页面。

这样可以先证明“演进是否真的产生稳定收益”，再扩大系统能够改变的范围。
