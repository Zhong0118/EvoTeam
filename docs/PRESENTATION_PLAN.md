# EvoTeam 汇报内容规划

汇报围绕一条可核验主线展开：固定起点执行任务，跨任务积累证据，达到阈值才修改 Strategy，独立验证后晋级，稳定时停止探索。主案例固定使用项目计划资源冲突。

## 内容顺序

| 页组 | 要讲清的问题 | 图示或证据 |
| --- | --- | --- |
| 项目定位 | EvoTeam 做什么，为谁服务 | 经验驱动的多智能体组织演进系统；主任务输入与输出 |
| 问题与边界 | 任务内补救怎样区别于跨任务更新 | Retry / Reflection 与 Strategy 版本变化对照 |
| 主场景 | 为什么从项目计划开始 | 人员、依赖、期限、预算与可校验硬约束 |
| 固定起点 | 第一次任务怎么跑 | 固定 Role Pool 与 Planner → Executor → Critic v0 |
| 核心对象 | 到底什么在演进 | Role → AgentConfig → AgentInstance；Strategy 与 Team 的关系 |
| 六层架构 | 各模块放在哪里 | 输入、能力、策略、运行时、观察经验、离线治理 |
| 两个闭环 | 哪些每次工作，哪些只在触发后工作 | Orchestrator / Evaluator / Monitor 与 EvolutionManager / Validator |
| 触发与经验 | 为什么这次需要改变 | 多 Run 模式、支持样本、反例、Policy 阈值 |
| 归因 | 错误产生与漏检发生在哪里 | Origin、Control、传播路径与检查器证据 |
| 候选 | 同一个问题有哪些受约束改法 | Prompt A、Tool Policy B、Verifier 结构 C 的 Diff |
| 独立验证 | 怎么知道候选更好 | 相同任务和资源条件，Evaluator → Validator → Gate |
| 成本与裁剪 | 增加节点是否值得 | 质量/成本、消融、REMOVE / CONDITIONALIZE |
| 生命周期 | 什么时候不再演进，退化怎么办 | Current → Stable → Reopen；Reject 与 Rollback |
| 框架边界 | EvoTeam 与 openJiuwen 分别负责什么 | Domain → RuntimeProtocol → Adapter → openJiuwen |
| 实验与进度 | 已证明什么，还未完成什么 | 三类任务、对照、P0–P5 实际状态 |

页数与版式按汇报时长安排，不在本文另建一套产品需求。

## 必备图与证据

架构图直接使用 [ARCHITECTURE.md](ARCHITECTURE.md) 的六层、两个闭环及生命周期定义，不再讲当前范围内的 Strategy Family 树。系统控制器、业务 Agent、评价模块与数据对象采用不同标识，避免把它们画成平级 Agent。

实现前只展示机制示例，并标注未运行。实现后展示真实的 Run / Strategy / EvolutionRecord 身份、失败传播、三个候选及 Gate 理由；至少有拒绝或回滚证据，不能只挑成功样本。

## 表达约束

- 三个创新固定为 Strategy as Evolvable Organization、Evidence-driven Bounded Organization Mutation、Evolution Governance。
- 不把 Prompt 自动优化、多 Agent 数量或记忆检索单独当作项目的核心成果。
- 不把“每个任务重新组队”“每次运行都演进”作为默认行为。
- 不宣称已经实现 Role Discovery、Family、分支合并、模型训练或递归自改。
- 不预填质量提升百分比；区分目标、机制示例、校准参数和测量结果。
- 相关工作只讲有原文支持的比较维度，不作其他平台“不具备某能力”的绝对断言。

实验口径统一引用 [EXPERIMENTS.md](EXPERIMENTS.md)，阶段状态统一引用 [ROADMAP.md](ROADMAP.md)。旧 HTML 汇报已不适配当前方案，正式演示稿在本提纲与真实证据基础上重新制作。
