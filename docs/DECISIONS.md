# EvoTeam 冻结决策

本文件记录当前有效决策，直接取代早期并行草案。产品与架构基线已冻结；效果仍需实验验证，参数仍需按协议校准。开发不能因为参数未定而重新开放已确定的产品范围。

## 1. 依据与优先级

本轮依据为飞书 v2/v3 最终讨论与项目计划书 V4。v3 中更晚的职责澄清覆盖早期示例；V4 中的六个 P0 决策明确主场景、固定角色池、单条版本链及当前白名单。v1 只用于理解来源，不再作为并列实现规范。

| 来源 | 用途 |
| --- | --- |
| [10 v2 范围敲定](飞书讨论结果/10-v2-范围敲定.md) | Strategy 与能力配置、Team、Workflow 的关系 |
| [11 v3 整体概念明确](飞书讨论结果/11-v3-整体概念明确.md) | Role、AgentConfig、AgentInstance、Strategy 与 Run 的区分 |
| [14 v3 五个问题](飞书讨论结果/14-v3-5个问题.md) | 固定 v0、事件触发、Stable、控制器及 Prompt 四层边界 |
| [15 v3 补充](飞书讨论结果/15-v3-补充.md) | ExperienceStore / Aggregator、Monitor、正负经验 |
| [16 v3 模块职责](飞书讨论结果/16-v3-六大评级模块.md) | 领域模型与 Runtime 解耦，组件身份、时机与职责 |
| [17 v3 架构位置](飞书讨论结果/17-v3-评级模块所处位置-和之前架构对比.md) | 最终六层与两个闭环，Candidate 生命周期位置 |
| [项目计划书 V4](EvoTeam_项目计划书_V4_概念冻结与架构闭环版.docx) | 项目申请口径、六个 P0 决策、主任务、归因时点、验收与实施阶段 |

原始导出包含仅保留引用标记的飞书 sheet，不能据此恢复未导出的单元格。当前决策均依据可读正文及计划书实际表格，不猜测缺失内容。原始记录只作来源留存，现行规范按 README 导航阅读。

## 2. 已冻结决策

| 编号 | 决策 | 原因与约束 |
| --- | --- | --- |
| F01 | 经验驱动的多智能体组织演进系统 | 核心演进对象为 Strategy，长期改变必须影响未来任务 |
| F02 | 复杂项目计划生成与校验为主场景 | 硬约束可程序验证，支持定位错误与成本比较 |
| F03 | 固定 Role Pool，固定 Planner → Executor → Critic v0 | 保持可复现起点，区分任务内适配和历史驱动演进 |
| F04 | RoleDefinition、AgentConfig、AgentInstance 分离 | 职责固定、配置版本化、运行状态隔离；统一使用 AgentConfig 名称 |
| F05 | Strategy = AgentConfig[] + Topology + OrchestrationPolicy + VersionMetadata | 组织定义保持清晰，证据与治理过程独立存入 EvolutionRecord |
| F06 | 六层概念模型与在线/离线两个闭环 | 六层不等同六个服务，离线演进不嵌入每次业务执行 |
| F07 | Orchestrator 与 EvolutionManager 是确定性控制器 | LLM 仅参与局部解释与提案，不掌握触发和晋级规则 |
| F08 | Critic / Verifier 在 Team 内，Evaluator 在 Run 后 | 执行方审查不能代替独立评分 |
| F09 | StrategyMonitor 跨 Run 检测 Trigger | 定期检查不等于定期演进，样本不足继续收集 |
| F10 | Validator 组织批量实验，Gate 按规则裁决 | 实验执行、单 Run 评分与晋级判断分离 |
| F11 | Experience 是数据，Store 与 Aggregator 分工 | 保留支持样本、反例、范围、置信度与验证历史 |
| F12 | Outcome Attribution 包括失败、贡献与改进 | Origin / Control 在候选前，边际贡献跨 Run，改进归因在验证后晋级前 |
| F13 | 受约束、最小 Mutation | AgentConfig 增删/替换、Prompt/Tool Policy 更新、Rewire、Conditionalize；固定 Role 与权限边界 |
| F14 | 单条正式 Strategy 版本链 | Family、分支、继承、合并和父策略晋级不进入当前范围 |
| F15 | STABLE 停止主动搜索，异常达到阈值才 Reopen | 防止无效搜索、过度演进和版本反复切换 |
| F16 | Reject 与 Rollback 分开 | Reject 拒绝未上线候选；Rollback 撤下已上线退化版本并恢复旧版本 |
| F17 | History、Validation、Final Test 隔离 | 候选生成不能读取验证答案，最终测试不能用于反复选策略 |
| F18 | Planner 不默认检索历史 Experience | 保持 Experience → Evolution → Strategy 变化这条主因果路径 |
| F19 | Python 3.12、uv、Pydantic、openJiuwen Core | Domain 与 SDK 解耦，只在 Runtime Adapter 中直接依赖框架 |
| F20 | 不进行模型训练、递归自改或自动权限扩展 | 当前验证受控组织演进，不扩张为开放式系统自修改 |

上述决策整合当前有效内容，不保留旧版 Accepted / Proposed 的矛盾表。以后确需改变产品边界时，必须由团队明确提出，并同步改写相关规范；普通实现细节不应演变为重新设计产品。

## 3. 仍需校准或具体化的内容

| 项目 | 处理方式 | 必须完成的时点 |
| --- | --- | --- |
| Task / Constraint Schema、输出 Schema、检查器语义 | 将主场景转为明确的字段、单位、约束规则与正反例 | P0，在线业务实现前 |
| window_size、min_samples、重复失败阈值 | 用固定 v0 的正常波动校准 | 主演进实验前 |
| quality_drop、cost_overrun、low_contribution 阈值 | 指定指标口径、基线及比较方向后校准 | Monitor 与 Gate 实验前 |
| cooldown、max_candidates、演进总预算 | 开发者定义资源限制并版本化登记 | 演进流程启用前 |
| Stable、Reopen 与 Rollback 的数值条件 | 使用连续窗口、严重错误与退化证据制定测试用例 | 生命周期验收前 |
| 验证集规模、重复次数、种子、负迁移门槛 | 依据任务难度、波动和预算预注册 | Candidate 比较前 |
| 质量收益与效率收益的具体 Gate | 设质量底线、最小收益、成本/延迟边界，禁止事后改权重 | 正式比较前 |
| 模型、Tool 版本与 Runtime API 映射 | 集成验证后锁定可复现组合 | 真实 v0 运行前 |
| 前端具体组件与页面实现 | 保持证据展示需求，按 P5 定具体方案 | UI 开发前 |

讨论中的窗口 10、候选 3、收益百分比和示例分数均为说明，不是已测量结果或强制默认值。架构冻结不意味着这些数值已被确定。

## 4. 文档职责与清理

README 为总入口；PROJECT 定范围，ARCHITECTURE 定概念和模块，EXPERIMENTS 定评价协议，ROADMAP 定实施顺序，PRESENTATION_PLAN 定汇报内容，RELATED_WORK 保存参考入口。DEVELOPMENT 与 AGENTS 管工程流程。

重复的 PRODUCT_VISION、旧 PROJECT_PROPOSAL、旧讨论汇总及 docs/v1 文档集已由现行主题文档替代。旧 HTML 汇报中的动态首次组队与 Family 叙事也不再适用，移出当前文档集。保留 V4 项目计划书和飞书原始记录供追溯，不再复制出另一套带版本后缀的实现规范。
