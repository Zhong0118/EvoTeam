

## 定位与目标

EvoTeam 是基于 openJiuwen Core 的经验驱动多智能体组织演进系统。面向 Agent 开发者、研究者和应用研发团队，交付可运行的组织演进原型、实验工具及可解释的展示界面。

系统学习的对象是组织方案 Strategy：使用哪些 AgentConfig、给它们分配什么能力、怎样通信、怎样调度与停止。一次任务内的 Retry、Reflection、Replan、条件路由和上下文检索本身不构成跨任务演进。

一次有效演进必须形成完整证据链：历史 Run → 稳定信号 → Trigger → Attribution → 受约束 Mutation → Candidate Strategy → 独立验证 → Promote → 影响未来任务。未通过验证的 Candidate 被拒绝；晋级后退化的版本可以回滚。

## 主任务与交付物

主场景固定为复杂项目计划生成与校验。

| 项目 | 内容 |
| --- | --- |
| 输入 | 项目目标、工作项、人员及能力、依赖、期限、预算、硬约束 |
| 输出 | 任务分解、里程碑、排期、资源分配、风险清单、调整说明及校验依据 |
| 主要错误 | 资源冲突、依赖遗漏或循环、期限违反、预算超限、必要内容缺失 |
| 主要质量标准 | 硬约束满足率、计划完整性、可执行性 |
| 起始团队 | PlannerConfig → ExecutorConfig → CriticConfig |
| 首个演进案例 | 资源冲突反复发生，定位错误产生点及漏检点，比较 Prompt、Tool Policy 与结构修改 |

报告生成和数据分析是另外两类可复现任务，用较小规模验证机制适用性。它们不改变主场景优先级，也不要求实现 Strategy Family。首轮先完成项目规划的一条版本链，再扩展独立任务套件。

## 固定起点与运行规则

Role Pool 固定为 Planner、Executor、Researcher、Analyst、Writer、Verifier、Critic。Role 只定义职责；同一 Role 可以通过不同 AgentConfig 专业化，例如资源校验和数值校验都引用 Verifier。

普通任务使用已晋级的当前 Strategy。Orchestrator 根据 TaskProfile 执行其中已经定义的条件，不临场创造新 Role、组织策略或权限。v0 固定使用三个节点，为后续实验提供一致起点。

Planner 不将历史 Experience 检索作为基线常规输入。历史对未来任务的主要影响路径是 Experience → Evolution → Strategy Version Change，避免混入记忆检索收益。

StrategyMonitor 跨 Run 观察表现；窗口到期只是检查时机。只有达到已登记规则才启动 EvolutionManager。稳定策略继续服务任务并监控，不持续生成 Candidate。

## 当前范围

- EvoTeam 领域模型、RuntimeProtocol 与 openJiuwen Adapter。
- 固定 v0、结构化 Agent 协作、任务内审查、Run 与 Trace。
- 独立 Evaluator、不可修改的 SealedRun、正负经验聚合与长期监控。
- Failure Attribution 的 Origin / Control、Contribution Analysis、验证后的 Improvement Attribution。
- 单条 Strategy 版本链上的 AgentConfig 增删/替换、Prompt 更新、Tool Policy 更新、Rewire、Conditionalize。
- Candidate 隔离验证、规则 Gate、Promote / Reject、Stable / Reopen / Rollback。
- 三类任务、对照与消融、归因基准、结果与成本统计。
- Team Graph、Trace、归因证据、Candidate Diff、验证结果和版本时间线展示。

Skill 是 AgentConfig 的能力维度，通过已登记能力引用进行配置；当前不额外开放自动编写任意 Skill 或独立 Skill 搜索体系。模型与 Tool 的实现版本在受控比较中保持一致。

## 当前不做

- 自动创造或改写 RoleDefinition。
- Strategy Family、任务分支、继承、合并、父策略晋级与跨 Family 泛化。
- 基础模型训练、权重自改、递归自我改进或演进引擎修改自身规则。
- 自由生成任意程序或 Workflow、无界循环、无预算的 Candidate 搜索。
- 自动新增 Tool、扩大权限、降低安全规则或开放外网。
- 生产 Canary、复杂分布式部署和以替代 Agent Framework 为目标的重建。

当前以离线数据、受控工具和可程序验证任务完成闭环。上述未来能力不能作为当前阶段必做需求进入实现。

## 三个核心创新

| 创新 | 要证明的内容 |
| --- | --- |
| Strategy as Evolvable Organization | AgentConfig、能力分配、Topology、OrchestrationPolicy 统一为可版本化的组织方案 |
| Evidence-driven Bounded Organization Mutation | 历史证据与归因决定修改对象，固定 Role Pool 和白名单限制搜索空间，同时支持增长与裁剪 |
| Evolution Governance | 触发、验证、晋级、停止、重开与回滚组成完整生命周期 |

这些是项目的设计与验证目标，不能在尚未取得结果时宣称已证明优于现有系统。Prompt 或 Tool 的更新是 Strategy 的修改维度，不能单独代替组织演进的验证。

## 验收标准

1. 至少三类功能 Agent 稳定完成主任务，保留结构化协作记录。
2. Task、Strategy 版本、Team、AgentInstance、Run、Trace、Evaluation 可相互追溯。
3. 正常窗口不触发演进；重复失败或退化达到阈值时产生有证据的 Trigger。
4. 至少一类可程序验证错误完成 Origin 与 Control 定位。
5. 能生成 Prompt、Tool Policy、Structure 三类单项 Candidate；结构修改包含必要的节点与连边调整。
6. Current 与 Candidate 在隔离 Validation Set 上公平比较质量、成本与稳定性。
7. 支持拒绝候选、晋级、稳定停止、重新触发及退化回滚。
8. 展示一次真实的跨任务版本变化与后续影响，同时保留失败候选证据。
9. 项目规划、报告生成、数据分析提供固定输入、评价规则与运行记录。
10. 汇报明确区分机制示例、目标门槛和实际测量结果。

具体实验与阶段退出条件分别见 [实验](EXPERIMENTS.md) 和 [路线图](ROADMAP.md)。
