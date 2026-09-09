# EvoTeam Agent 开发约束

## 1. 角色与依据

Coding Agent 是项目实现者，不替团队重新定义产品。开发前必须阅读：

```text
README.md
DEVELOPMENT.md
AGENTS.md
docs/PROJECT.md
docs/ARCHITECTURE.md
docs/ROADMAP.md
```

演进、评价或实验任务还必须阅读 `docs/EXPERIMENTS.md`、`docs/DECISIONS.md`。

当前规范已经按飞书 v2/v3 最终讨论与 V4 项目计划书统一。原始讨论保留用于追溯，不将早期 Family、动态首次组队或示意代码重新升级为当前需求。遇到真正的核心决策冲突应指出，不擅自改架构；普通实现细节在既定边界内处理。

## 2. 技术基线

Python 3.12、uv、Pydantic、openJiuwen Core。依赖统一使用 `uv add`、`uv add --dev`、`uv sync`、`uv run`；不使用 pip / conda 管理正式依赖。

只有 `runtime/openjiuwen/` Adapter / Integration 层可以直接 import openjiuwen。Domain、Orchestration、Evaluation、Experience、Monitoring、Evolution 只依赖自己的模型和接口。Fake Runtime 用于测试，不替代最终真实 openJiuwen 集成。

不主动引入 LangGraph、AutoGen、CrewAI、Kafka、Redis、Kubernetes、微服务、Celery、训练框架或大型向量数据库。后端与前端的实际状态见 DEVELOPMENT，不把候选技术写成已有实现。

## 3. 冻结的产品与领域规则

- 主场景是复杂项目计划生成与校验；报告、数据分析用于补充可复现验证。
- 固定 Role Pool：Planner、Executor、Researcher、Analyst、Writer、Verifier、Critic。自动演进不得创造或改写 RoleDefinition。
- 初始 Strategy v0 固定为 Planner → Executor → Critic，不在每次任务中自由生成组织。
- 统一使用 AgentConfig 表达稳定配置；AgentInstance 持有本次 Run 状态；Team 是实际启用的实例与协作关系。
- Strategy 包含 AgentConfig、Topology、OrchestrationPolicy 与 VersionMetadata；EvolutionRecord 独立保存证据、归因、验证和决定。
- 当前只验证单条正式 Strategy 版本链，不实现 Family、分支、继承、合并、父策略晋级。
- Planner 不默认检索历史 Experience；主要跨任务影响路径必须经过 Strategy 版本变化。

## 4. 执行与评价边界

Agent 通过 Orchestrator 通信，不直接互调；输入输出优先使用 Pydantic Schema，不让下一个 Agent 从自由文本猜结构。

Orchestrator 负责实例化、调度、结构化消息、Retry、Timeout、Budget 与 Trace。Critic / Verifier 是 Team 内质量控制 Agent；Evaluator 在 Run 后独立评分；StrategyMonitor 跨 Run 判断 Trigger；Validator 组织 Current / Candidate 实验；Gate 按规则裁决；EvolutionManager 组织离线流程并执行生命周期操作。

这些模块不能合成统管一切的超级 Agent。LLM 可以辅助归因与候选提案，不能自行改阈值、放宽权限或决定绕过 Gate。

## 5. 演进约束

Retry、Reflection、Replan、临时上下文和条件路由本身不算跨任务演进。长期变更必须走：

```text
Experience → Monitor Trigger → EvolutionManager → Attribution
→ Bounded Mutation → Candidate → Validator → Improvement Attribution
→ Validation Gate → Promote / Reject → Future Tasks
```

普通任务不修改当前 Strategy；一个 Run 固定配置快照。Candidate 与 Current 使用同一数据模型，但 Candidate 只在隔离验证中执行。验证 Run 不污染线上 Monitor，不触发递归演进。

白名单为 AgentConfig 增删/替换、Prompt / Tool Policy 更新、Rewire、Conditionalize。固定 Role 与授权能力边界，禁止任意代码生成、无界循环、自动新增 Tool 或扩大权限。模型版本在受控比较中保持一致。

Prompt 使用版本化资产和固定引用，不能直接覆盖旧模板。Role 职责、用户输入和运行上下文不作为 Prompt Mutation 对象。

STABLE 停止主动搜索并继续服务；新证据达到阈值才 Reopen。Reject 拒绝未上线候选，Rollback 撤下已上线退化版本并恢复可用历史版本。样本不足不能默认晋级。

## 6. 证据与实验

核心步骤产生统一事件，保留输入来源、消息、工具、结果、成本与终止原因。成功、失败、超时、取消均留档；SealedRun 封存后不可修改。

Experience 保留支持样本、反例、置信度、适用范围与验证历史。Failure Attribution 区分 Origin / Control；Contribution Analysis 支持裁剪；Improvement Attribution 在验证后、晋级前完成。

History / Evolution、Validation、Final Test 相互隔离。候选生成不读取验证答案，最终测试不用于反复选候选。比较同任务、模型、Tool 版本、随机参数、评价器和预算，记录质量、成功率、Token/成本、延迟、Agent 数、Retry 和离线演进成本。

阈值由开发者定义规则、v0 基线校准后冻结；不得把飞书示例数值当作最终参数或实际结果。高影响或不确定归因使用消融/反事实证据，避免每个 Run 无条件运行昂贵实验。

## 7. 修改原则与验证

只实现当前任务范围，保持接口兼容，不做无关重构。新功能补有意义的测试。架构是目标约束，进度以实际代码为准，文档与实现不一致时明确指出。

完成任务前执行：

```bash
uv sync
uv run pytest
uv run ruff check .
```

已声明 Pyright 时同时执行 `uv run pyright`。无测试、工具失败或检查未运行都必须如实报告，不能宣称通过。

## 8. Git 与汇报

初始化阶段允许完善 main 文档及骨架；正式功能开发采用任务分支与 PR。分支属于任务，不属于个人。不要提交凭据、.venv、.env、运行数据库或系统缓存。

完成后汇报：

```text
## 完成内容
## 修改文件
## 关键设计决策
## 测试
## 尚存风险
## 未完成 / 未处理
```

原始讨论与计划书保留为来源，现行文档直接维护最终内容，不叠加互相冲突的补丁、批注或平行版本。
