# EvoTeam

EvoTeam 是基于 openJiuwen Core 的经验驱动多智能体组织演进系统。它根据跨任务执行证据，对可版本化的 Strategy 进行受约束修改，经独立验证后改变未来任务默认采用的组织方式。

主场景是复杂项目计划生成与校验。初始 Strategy v0 固定为 **Planner → Executor → Critic**；Role Pool 由开发者定义。系统平时执行当前策略，只有重复失败、性能漂移、成本异常或低贡献证据达到阈值才启动离线演进。策略稳定后进入 STABLE，停止主动探索，继续监控。

```text
在线执行：Task → Current Strategy → Orchestrator → Team / AgentInstance
         → Run → Evaluator → SealedRun → Experience → StrategyMonitor

离线演进：Trigger → EvolutionManager → Attribution → Mutation → Candidate
         → Validator → Improvement Attribution → Validation Gate
         → Promote / Reject → 后续任务使用已验证的 Strategy
```

## 当前状态

产品与架构已按最终讨论统一。初始 v0 仍为 Planner → Executor → Critic；执行器现支持可选 Verifier 的受限无环图和一次 Critic→Executor 有界返工。已接入 openJiuwen 0.1.17.post1 的真实 ReActAgent，提供 init/run/observe/evolve 入口、SQLite Trace/快照、重复失败监控、Prompt 与新增 Verifier 两类 Candidate、多候选比较和原子生命周期。AttributionReport、MutationProposal、ValidationResult 与 EvolutionRecord 均可完整读取。DeepSeek 已完成复杂任务、有界返工及 Prompt/Verifier 多候选真实 Gate Reject 回归；漂移/成本/贡献监控、Tool/Skill Policy 与更通用结构 Mutation 尚未完成。

第一次接手建议先读 [模块关系与系统运行指南](docs/SYSTEM_WALKTHROUGH.md)，运行示例后沿调用链阅读代码。完整文件索引见 [开发说明](DEVELOPMENT.md)，未完成阶段见 [路线图](docs/ROADMAP.md)。具体实验阈值仍需基线校准。

## 阅读入口

| 文档 | 唯一职责 |
| --- | --- |
| [系统运行指南](docs/SYSTEM_WALKTHROUGH.md) | 实际模块关系、运行路径、数据契约、演示及后续开发入口 |
| [项目定义](docs/PROJECT.md) | 产品目标、主场景、范围、创新与验收 |
| [架构](docs/ARCHITECTURE.md) | 术语、六层职责、两个闭环、模块与数据契约 |
| [决策](docs/DECISIONS.md) | 已冻结决策、来源与仍需校准的参数 |
| [实验](docs/EXPERIMENTS.md) | 数据隔离、对照、归因、Gate 与可复现要求 |
| [下一轮实施计划](docs/NEXT_STEPS.md) | 数据库升级、数据隔离、逐任务验证与真实基线的执行任务 |
| [路线图](docs/ROADMAP.md) | P0–P5 实施顺序与阶段验收 |
| [汇报规划](docs/PRESENTATION_PLAN.md) | 面向最终方案的汇报结构与证据要求 |
| [相关工作](docs/RELATED_WORK.md) | 既有参考文献入口与后续核验范围 |
| [Demo 测试报告](docs/DEMO_TEST_REPORT.md) | 初代测试记录与最新 DeepSeek 真实回归 |
| [版本对比](docs/VERSION_COMPARISON.md) | main 与组员分支增量、审查修复、当前进展及后续次序 |
| [开发说明](DEVELOPMENT.md) | 实际环境、依赖与验证命令 |
| [Agent 约束](AGENTS.md) | 实现必须遵守的边界 |

## 设计依据

[项目计划书 V4](docs/EvoTeam_项目计划书_V4_概念冻结与架构闭环版.docx) 是项目申请材料；[飞书讨论结果](docs/飞书讨论结果/) 保留原始讨论。现行文档以 v2/v3 最终结论与 V4 计划书统一后的基线为准。原始记录中的早期方案、示例数字与示意代码不能直接作为实现要求；来源映射见 [决策](docs/DECISIONS.md)。

## 技术基线

Python 3.12、uv、Pydantic、openJiuwen Core。后端相关依赖已经声明；前端选型与开工安排见开发说明。EvoTeam 自己维护领域对象，只有 Runtime Adapter 直接依赖 openJiuwen SDK。

```bash
uv sync
uv run python -m evoteam roles
uv run python -m evoteam v0 --model-id preview --model-version draft
uv run python -m evoteam demo --database /tmp/evoteam-demo.sqlite3
```

`roles`、`v0` 只预览配置，v0 输出为 DRAFT。`demo` 使用手写产物执行真实调度、规则评价和 SQLite 封存，数据库路径必须不存在；重复运行请换新文件名。演示不调用模型，不能作为质量或演进实验结果。完整开发与检查方式见 [DEVELOPMENT.md](DEVELOPMENT.md)。

## 本地 DeepSeek API

项目已预留 DeepSeek V4 Flash 的 OpenAI-compatible 配置和 FastAPI 接口：

```bash
cp .env.example .env
# 在 .env 中填写 EVOTEAM_MODEL_API_KEY
uv sync
uv run python -m evoteam serve
```

服务启动后可访问 `http://127.0.0.1:8000/docs`。接口包括：

- `GET /health`：检查本地服务和模型标识；
- `POST /v1/initialize`：登记初始 Strategy 并初始化数据库；
- `POST /v1/runs`：执行 Planner → Executor → Critic；
- `POST /v1/observe`：观察历史并检查重复失败 Trigger。
- `POST /v1/evolve`：显式启动一次受限 Prompt/Verifier 候选比较；无 Trigger 时不调用模型。

VS Code 中也可直接运行 `EvoTeam API (DeepSeek)` 调试配置。真实 `.env` 已被忽略，不会进入 Git。
