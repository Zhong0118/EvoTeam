# EvoTeam 开发说明

## 当前仓库状态

已有项目规划 v1 契约、规则评价、受限 3/4 节点 DAG、一次有界返工、SQLite 封存和无模型演示。已接真实 openJiuwen ReActAgent、init/run/observe/evolve、重复错误监控、Prompt/Verifier 多候选、配对验证、Gate 与生命周期。归因、提案、验证和治理记录已落库；审查补齐了 Trigger 原子消费、取消终止、公平比较与 Gate 缺失证据阻断。SQLite 已提供显式备份迁移入口；DeepSeek 已完成真实 Gate Reject 实验，其他监控信号、Tool/Skill 演进、更通用结构 Mutation 和前端仍待完成。

开发前阅读 README、AGENTS、PROJECT、ARCHITECTURE、ROADMAP；演进和评价工作同时阅读 EXPERIMENTS、DECISIONS。产品与架构按最终讨论冻结，现有骨架按 P0–P5 逐步填充逻辑。

## 环境初始化

目标 Python 3.12，依赖统一使用 uv 管理：

```bash
uv sync
uv run python --version
```

若本机缺少目标 Python：

```bash
uv python install 3.12
uv sync
```

不需要重新 `uv init`，也不要求手动激活虚拟环境。用 `uv add`、`uv add --dev` 修改依赖，更新并提交 pyproject.toml 与 uv.lock；不要用 pip 或 conda 管理正式依赖。

## 技术与实现边界

| 项目 | 当前情况 |
| --- | --- |
| Python | .python-version 指向 3.12；pyproject 当前要求 >=3.12，项目验证以 3.12 为准 |
| Agent Runtime | openJiuwen Core，只有 runtime/openjiuwen Adapter 直接使用 SDK |
| 数据契约 | Pydantic；Domain、Strategy 和证据对象由 EvoTeam 自己维护 |
| 后端相关依赖 | 已实现最小 FastAPI health/init/run/observe/evolve 接口；暂无鉴权与前端 |
| 持久化相关依赖 | 已声明 SQLAlchemy、Alembic；首轮按单机 SQLite 路径实现 |
| 前端 | React + TypeScript 仍为候选，仓库没有前端工程；具体组件在 P5 确定 |
| 检查工具 | pytest、pytest-asyncio、Ruff、Pyright 已配置，基础契约与边界测试位于 tests/ |

具体包版本以锁文件为准。接入前验证锁定版本的 SDK API、异步行为、结构化输出、Tool 与事件回调，不能把飞书示意代码中的类名当作真实 SDK 接口。

## 实现顺序

先做可序列化领域模型与项目计划约束正反例，再实现 Fake Runtime 下的行为测试和真实 openJiuwen Adapter。模块分布以 ARCHITECTURE 为准，阶段退出条件以 ROADMAP 为准。

Prompt 在版本化资产中保存，Strategy 引用固定版本。运行上下文与配置隔离，候选在验证模式执行，不能通过一个普通 Run 修改当前服务策略。

新功能补有意义的测试，优先覆盖约束、失败路径、隔离与生命周期。不要只测试字段赋值或复制示意实现。真实模型集成测试与无需模型的单元测试分开，凭据通过环境配置提供，不写入版本库或日志。

## 检查命令

```bash
uv sync
uv run pytest
uv run ruff check .
uv run pyright
```

测试覆盖固定配置、Prompt 引用、不可变边界、无副作用导入、SDK 依赖边界、离线 CLI，以及执行/评价/封存的顺序、无 Trigger 不演进、验证数据隔离和观察期间版本变更。另覆盖主任务正反例、真实 SQLite 重开与事务回滚、失败/超时/外部取消、预算、输入快照和消息来源。测试不代表真实模型与演进验收。Ruff 排除 docs 与历史汇报资源，避免自动格式化原始讨论里的示意代码。

## Git 与文件管理

初始化阶段可直接完善 main 文档和基础骨架。正式功能开发使用任务分支和 PR；遵循任务约定，不建立每人永久分支。

提交 pyproject.toml、uv.lock、.python-version、源码、测试、版本化配置和文档。`.env.example` 提供环境字段，不包含凭据；`.gitignore` 排除虚拟环境、真实 .env、运行数据库、缓存和系统文件。Settings 只在显式实例化时读取环境，模块导入不创建全局客户端、数据库或模型连接。

飞书讨论与项目计划书作为原始设计依据保留。实现规范只有 README 导航中的主题文档，不再新增平行 v1/v2/v3 草案。每次实现同步更新真实进度和可执行命令，不把计划写成已完成能力。


## 当前可运行入口

```bash
uv run python -m evoteam roles
uv run python -m evoteam v0 --model-id preview --model-version draft
uv run python main.py --help
uv run python -m evoteam demo --database /tmp/evoteam-demo.sqlite3
uv run python -m evoteam serve
```

`roles` 列出固定职责池；`v0` 输出可序列化的三节点 DRAFT 配置。preview/draft 是预览占位值，不是项目选定模型。`demo` 用手写产物运行真实调度与归档，要求全新数据库路径。正式 `init/run/observe/evolve` 的配置与命令见系统运行指南；`serve` 提供本地 FastAPI 包装。

初始骨架约定：缺失预算为 None，表示尚待配置；Retry/Replan 先为 0，表示未开启。这些是离线配置起点，不是实验校准结论。正式 v0 进入 CURRENT 前必须明确运行参数、能力引用和校验。项目采用仓库内 `python -m evoteam` 运行，暂不增加 wheel 构建或发布配置。

## Python 文件索引

所有包的 `__init__.py` 只说明职责，不初始化服务。下表覆盖各个业务 `.py`；模型中的 TODO 是具体校验或算法的后续实现位置，不表示已完成对应阶段。

### 入口与装配

| 文件 | 当前内容与后续职责 |
| --- | --- |
| `main.py` | 兼容仓库入口，转发 CLI |
| `evoteam/__main__.py` | 支持 python -m evoteam；导入不执行命令 |
| `evoteam/cli.py` | roles / v0 / demo 及正式 init/run/observe/evolve 命令 |
| `evoteam/entrypoints.py` | 正式 init/run/observe/evolve；登记模型绑定，在线与离线分离 |
| `evoteam/demo.py` | 在全新数据库运行手写示例，不污染真实历史 |
| `evoteam/bootstrap.py` | 构建固定 Planner → Executor → Critic DRAFT v0 |
| `evoteam/settings.py` | 环境配置及 SecretStr 凭据字段，无全局实例 |
| `evoteam/application.py` | 已实现 TaskService.execute、EvolutionService.inspect / evolve_if_needed 的模块调用顺序和身份检查 |
| `evoteam/composition.py` | 已实现无副作用依赖装配、共享执行/评价组件与 StoreEventSink |

### 领域模型

| 文件 | 固定内容与边界 |
| --- | --- |
| `domain/common.py` | Pydantic 基类、不可变模型、AssetRef、StrategyRef、预算类型 |
| `domain/role.py` | RoleType、RoleDefinition、只读七角色 ROLE_POOL |
| `domain/agent.py` | ToolPolicy、RuntimeConfig、AgentConfig、AgentInstance、消息与结果 |
| `domain/strategy.py` | Strategy、定义/版本信息、拓扑边、调度策略与生命周期枚举 |
| `domain/task.py` | Task / TaskProfile 与三类任务枚举；项目规划由专用解析器校验 |
| `domain/planning.py` | 项目规划 v1 输入、输出、Planner 分析与 Critic 审查；单位和引用校验 |
| `domain/events.py` | TraceEvent 与执行/治理统一事件名 |
| `domain/run.py` | Team、ExecutionPlan、RunResult、RunPurpose、SealedRun、完整 RunSnapshot |
| `domain/evaluation.py` | EvaluationIssue、RunMetrics、EvaluationResult；未知指标为 None |
| `domain/experience.py` | 正负经验、模式、Origin/Control/贡献/改进归因数据 |
| `domain/evolution.py` | Trigger、MonitorResult、Mutation 白名单、验证计划/结果、Gate、EvolutionRecord |

配置模型采用 frozen 与 tuple，运行对象使用独立实例和容器。SealedRun 保存不可变元数据与产物引用；SQLite 已实现不可覆盖、封存事务和完整快照落盘。Orchestrator 只接受固定三节点链或新增一个 Verifier 的四节点 DAG；任意图和动态能力注册仍不开放。

### 能力与 Runtime

| 文件 | 当前入口与后续职责 |
| --- | --- |
| `capabilities/registry.py` | Role/Prompt/Skill/Tool/Model 解析 Protocol；无真实动态 Registry |
| `capabilities/prompts.py` | 已登记 Prompt 引用到包内文件的只读映射及读取函数 |
| `runtime/protocol.py` | AgentRuntime、RuntimeAgent 句柄、RuntimeContext、EventSink |
| `runtime/fake.py` | FakeRuntime：按角色回传预置产物；只接受 fake@1，实际无模型用量 |
| `runtime/models.py` | 非敏感模型身份、连接与采样参数；独立 SecretStr 密钥 |
| `runtime/openjiuwen/adapter.py` | 已实现锁定 SDK ReActAgent，单次调用、JSON、用量、超时和上下文清理 |
| `tools/constraint_checker.py` | check：已实现资源、依赖、技能、期限、预算、完整性检查及定位证据 |

`evoteam/prompts/{planner,executor,critic,verifier}/v0.md` 保存初始模板。Verifier 仅是已准备的能力模板，不加入默认 v0。其他固定 Role 只有职责定义，具体 Prompt/Skill/Tool 配置随对应场景实现。业务 Agent 由 AgentConfig + Runtime 创建，不再为每个 Role 重复写一套 Python Agent 类。

### 执行、评价与经验

| 文件 | 当前方法与后续职责 |
| --- | --- |
| `orchestration/task_analyzer.py` | analyze：校验项目规划 v1 输入并提取约束引用 |
| `orchestration/orchestrator.py` | execute：已实现受限 DAG、多上游来源、一次 Critic 返工、Token/超时及有界清理 |
| `evaluation/evaluator.py` | Evaluator Protocol；evaluate 已独立校验唯一计划、保留失败，未知质量/用量保持 None |
| `evaluation/metrics.py` | MetricsCollector.collect：汇总唯一运行产物用量和执行耗时，失败缺失用量不伪造 |
| `experience/store.py` | ExperienceStore Protocol：保存正负经验及模式 |
| `experience/evidence.py` | 可比较窗口验证、错误码与确定性证据 ID |
| `experience/aggregator.py` | 已实现重复错误模式、支持 Run 与成功反例 |
| `monitoring/state.py` | MonitorState / Store，持久化观察历史与并发 revision |
| `monitoring/policy.py` | EvolutionPolicy：显式参数，无示例阈值默认值 |
| `monitoring/strategy_monitor.py` | inspect/observe：重复失败、样本量与冷却；不生成 Candidate |

### 演进与治理

| 文件 | 当前方法与后续职责 |
| --- | --- |
| `evolution/attribution.py` | Failure 依据封存产物与实际 Critic 输出；Improvement 描述比较差值；Contribution 待消融证据 |
| `evolution/mutation.py` | 已实现 UPDATE_PROMPT 与新增 Verifier 的 ADD_AGENT_CONFIG 提案、物化和静态检查 |
| `evolution/validator.py` | 已实现同数据集 Current/Candidate 配对执行、评价、汇总与 validation 封存 |
| `evolution/gate.py` | 质量、硬约束、Token、延迟和显式配对样本门槛；缺失受限证据不放行 |
| `evolution/lifecycle.py` | 已实现 Promote / Reject / Stable / Reopen / Rollback 合法转换 |
| `evolution/manager.py` | 已实现多个单因素候选的生成、独立验证、确定性选择和统一生命周期收尾 |

### 持久化与测试

| 文件 | 当前方法与后续职责 |
| --- | --- |
| `storage/protocol.py` | RunStore（含 seal_run 原子封存）、StrategyStore、EvolutionStore；显式用途与生命周期契约 |
| `storage/sqlite.py` | 运行、模型、经验、监控、唯一版本号、完整演进产物及生命周期原子切换 |
| `tests/test_evolution_governance.py` | 重复/并发消费、取消与父版本竞争收尾 |
| `tests/test_gate_review.py` / `tests/test_validation_review.py` | Gate 证据身份、成本与样本门槛、公平比较 |
| `tests/test_attribution_review.py` | 封存产物归因、Critic 漏检与候选身份 |
| `tests/test_evolution.py` | 无 API 的 Prompt 演进、配对验证、隔离、晋级与唯一版本号测试 |
| `tests/test_skeleton.py` | 初始契约、边界及 CLI 测试，不调用模型或数据库 |
| `tests/test_planning.py` | 项目规划输入与约束正反例、独立评价 |
| `tests/test_online.py` | 固定调度 + SQLite 端到端、故障、事务、快照、取消及 demo CLI |
| `tests/test_openjiuwen.py` | 实际 SDK 与本地 HTTP 协议、JSON、用量、重试边界 |
| `tests/test_runtime_entry.py` | 实际 SDK 全链路、模型绑定、超时/外部取消、历史观察 |
| `tests/test_monitoring.py` | 跨 Run 模式、冷却、重开数据库及并发检查 |
| `tests/test_live_provider.py` | 显式启用的真实模型冒烟；默认跳过 |
| `tests/test_application.py` | 使用记录调用的替身验证跨模块顺序、隔离、版本竞争与异常传播 |

上表中省略 `evoteam/` 的相对路径均以该包为根。Protocol 中的省略号只声明接口。当前结构演进只允许新增唯一 Verifier 及固定必要连边，不表示任意拓扑、Tool Policy 与贡献消融已经实现。


## 模块关系与下一步

模块图、在线与离线路径、项目规划 v1 字段语义、故障处理及贡献者阅读顺序统一放在 [系统运行指南](docs/SYSTEM_WALKTHROUGH.md)，本文件只维护环境与文件索引。

真实 SDK 在线闭环、DeepSeek Gate Reject 实验及 Fake Runtime 的多候选结构演进均已通过。下一项是扩充独立 History/Validation 数据并校准 Policy/Gate，再扩展监控信号和 Tool/Skill Candidate。总 Token 预算目前为响应后检测，只有输出 Token 上限传入请求；输入 Token 预估和严格费用上限尚未实现。

SDK 0.1.17.post1 的导入和 SSL 代码会产生上游弃用警告，当前测试保留这些警告；不将其隐藏成无警告结果。

Adapter 的清理直接使用 SDK 的公开 checkpoint/context 释放接口。锁定版本的 `ReActAgent.clear_session` 会经全局 Runner 导入无关 Team/Evolving 可选依赖，当前不走该路径，也不为此扩大项目依赖。

## SQLite 数据库升级与恢复

`init` 只创建全新数据库，不能用于给旧库补表。当前代码使用 SQLite `user_version=3`，只识别仓库历史中的 6 表基础布局、11 表演进布局和当前 12 表布局；表集合、列结构或版本标记未知时拒绝迁移。升级不会重建运行表，也不会改写 Strategy、Event、Run、Prompt 引用或活动 evolution claim。

升级前停止所有 `serve`、`run`、`observe` 和 `evolve` 进程，确保没有其他连接写数据库。备份参数必须指向尚不存在的新文件：

```bash
uv run python -m evoteam migrate \
  --database /absolute/path/evoteam.sqlite3 \
  --backup /absolute/path/evoteam.before-v3.sqlite3
```

命令先用 SQLite backup API 生成一致备份并执行 `PRAGMA quick_check`，成功后才以排他事务升级原库。6 表库会根据既有 Strategy 的最大版本初始化 `strategy_counters`；11 表库只补 `evolution_claims`；12 表库只校验并登记版本。成功输出：

```json
{"migrated": true, "schema_version": 3}
```

失败时不要删除备份或反复使用同一备份路径。先保持应用停止，使用 `sqlite3 <备份路径> 'PRAGMA quick_check;'` 验证备份；保留失败数据库作为独立文件，再把备份复制回原数据库路径。备份仍是迁移前布局：若继续使用当前代码，应为恢复后的库选择另一个新备份路径并重新执行迁移；若临时回退旧代码，则直接使用与该旧代码对应的备份布局。迁移不能恢复因进程硬退出遗留的活动 claim，也不会自动清除它。

本次 main 与功能分支的审查、进展和后续次序统一维护在 [VERSION_COMPARISON](docs/VERSION_COMPARISON.md)。新增 evolution_claims 表；旧数据库不能直接 open，升级需备份后显式建表并核验，不删除原始运行证据。当前没有自动迁移或进程崩溃后的 claim 恢复工具。
