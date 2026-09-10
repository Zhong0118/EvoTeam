# EvoTeam 实施路线图

产品和架构按最终讨论冻结。已实现项目规划 v1、规则评价、v0 三角色调度、可选 Verifier 受限 DAG、一次有界返工、SQLite 证据封存和真实 SDK。重复失败监控、Prompt/新增 Verifier 多候选、完整中间产物落库、配对验证、选择、Gate 与生命周期已实现，并完成一次 DeepSeek Gate Reject 实验；通用能力注册、其他监控信号、Tool/Skill Policy 与更通用结构 Mutation 仍待完成。实际运行入口见 [系统运行指南](SYSTEM_WALKTHROUGH.md)。

## P0 领域契约与可评价任务

目标：将冻结概念转为可测试契约，不重新设计产品。

- 定义固定 Role Pool、AgentConfig、Strategy、Topology、OrchestrationPolicy 与版本身份。
- 定义 Task / TaskProfile、项目计划输出、Constraint Schema 与明确单位。
- 建立最小任务正反例，明确资源、依赖、期限、预算的确定性评价规则。
- 定义 Run / Trace / Evaluation / SealedRun、Experience、Trigger、EvolutionRecord 契约。
- 定义 Runtime、Store、Evaluator 接口；用 Fake Runtime 测试不依赖模型的规则。
- 固定 v0 配置及版本化 Prompt；区分测试用参数和正式校准参数。
- 配置有效的 pytest、Ruff、Pyright 检查，完成当前依赖下的 openJiuwen 集成探针。

退出条件：领域配置可序列化与校验，非法引用/结构被拒绝；主任务正反例能独立判分；版本定义与运行状态分离。具体阈值留待 v0 数据校准，不阻塞无模型契约测试。

## P1 在线闭环

- 实现 openJiuwen Adapter：Agent 创建、结构化输出、允许的 Tool、异步调用及事件转换。
- 实现固定 Planner → Executor → Critic 的 Orchestrator。
- 控制结构化消息、有界返工、Timeout、Budget 与终止原因。
- 实现独立 Evaluator、Run / Trace / SealedRun 持久化。
- 核对成功、失败、超时和取消路径；禁止运行中写回 Strategy。

退出条件：真实 v0 能完成主任务并封存可重建的证据；没有 Trigger 时只执行当前策略；SDK 依赖只存在于 Adapter；文档记录可执行入口与实际限制。

## P2 经验与长期监控

- 实现 ExperienceStore 与 Aggregator，保存正负证据、范围与反例。
- 实现按策略版本、任务范围和运行用途分组的 StrategyMonitor。
- 用 v0 数据校准 window / min_samples、错误、成本、冷却等参数并登记 Policy 版本。
- 通过稳定窗口与故障注入测试 Trigger / No Trigger。

退出条件：多个 Run 能形成可追溯模式；正常波动不触发无意义演进，稳定状态不生成候选；验证 Run 不污染线上统计。

## P3 归因与受约束候选

- 实现 Origin / Control 归因与 Contribution Analysis。
- 实现 Mutation 白名单、结构/权限检查与有限 Candidate 生成。
- 同时覆盖 Prompt、Tool Policy、Structure 三类候选，支持必要的节点与连边修改。
- 实现 EvolutionManager 的流程组织和 EvolutionRecord，不把评分权集中到控制器。
- 高影响或低置信度情况补充消融/反事实证据。

退出条件：Trigger 后能生成少量合法、可解释、可比较的 Candidate；每个候选有唯一身份、父版本、Diff 与证据，不能直接服务正式任务。

## P4 独立验证与生命周期

- 实现 Validator，复用 Orchestrator + Evaluator 做隔离配对实验。
- 实现 Improvement Attribution 与确定性 Gate。
- 实现 Promote / Reject、Stable / Reopen / Rollback，保留恢复目标与审计。
- 验证多个候选全部失败、数据不足、晋级后退化、稳定后新错误等路径。
- 完成资源冲突案例，允许较便宜的 Tool Policy 胜出，不预设增加 Agent 的结论。

退出条件：形成真实 v0 → Candidate → Current 的后续影响，及 Reject / Stable / Reopen / Rollback 证据；候选生成不能访问验证答案，版本切换不影响已开始的 Run。

## P5 三类实验与可视化

- 完成项目规划主要实验，增加报告与数据分析的较小任务套件。
- 完成 Single Agent、Fixed Multi-Agent、Retry、无历史动态适配与 Mutation 消融。
- 运行 Attribution Benchmark、成本、负迁移与停止条件实验。
- 展示六层、两个闭环、Team Graph、Trace、归因、Candidate Diff、Gate 与版本时间线。
- 产出复现脚本、实际运行说明、结果、汇报与演示材料。

退出条件：三类任务可复现，真实结果与示意分开，能回答为何触发、改了哪里、为何晋级/拒绝、何时停止及怎样恢复。

## 实施次序与分工

核心证据与治理能力按 P0 → P1 → P2 → P3 → P4 的依赖推进；P5 的实验验收依赖相应证据，可视化页面、只读数据接口和 PPT 设计可提前并行。推荐一位组员负责核心后端，一位负责展示接口/前端/PPT，负责人承担数据、实验和集成验收；按实际技能调整，详细任务见 NEXT_STEPS。

结构 Mutation 属于核心闭环验收，不再沿用“先做完整 Prompt 产品，之后才考虑 Team Evolution”的路线。UI 随已有证据逐步实现，不能用静态展示替代尚未运行的治理机制。

下一步固定已接入模型的配置与独立任务分区，扩充 History / Validation / Final Test 数据，统计基线后预注册 Monitor 与 Gate。随后补逐任务配对指标、负迁移检查和真实晋级后的未来任务验证，再开展 Tool Policy、贡献消融及自动生命周期实验。运行命令见 [SYSTEM_WALKTHROUGH.md](SYSTEM_WALKTHROUGH.md)，本次审查与分工建议见 [VERSION_COMPARISON.md](VERSION_COMPARISON.md)。P2–P4 不因少量模型调用或可控 Fake Runtime 晋级测试通过就整体验收。

近期任务与分工见 [并行开发与交付计划](NEXT_STEPS.md)：N1–N4 为核心线，B0–B4 为展示/PPT线。它不是完整第一版的全部任务；Tool/贡献消融、自动治理和三类实验仍按本路线图验收。PPT逐页内容与布局见 [汇报设计](PRESENTATION_PLAN.md)。
