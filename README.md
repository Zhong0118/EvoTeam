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

产品范围、核心概念、六层架构和两个闭环已按最终讨论统一，进入实现准备阶段。仓库目前只有依赖配置与 `main.py` 占位入口，尚未实现上述业务模块，也没有可运行的 EvoTeam 服务或实验结果。

本轮先完成文档整理；代码开发按 [路线图](docs/ROADMAP.md) 从 P0 领域契约与主任务评价器开始。架构基线不再作为开放式头脑风暴反复改写；具体阈值在基线实验后校准、登记并冻结。

## 阅读入口

| 文档 | 唯一职责 |
| --- | --- |
| [项目定义](docs/PROJECT.md) | 产品目标、主场景、范围、创新与验收 |
| [架构](docs/ARCHITECTURE.md) | 术语、六层职责、两个闭环、模块与数据契约 |
| [决策](docs/DECISIONS.md) | 已冻结决策、来源与仍需校准的参数 |
| [实验](docs/EXPERIMENTS.md) | 数据隔离、对照、归因、Gate 与可复现要求 |
| [路线图](docs/ROADMAP.md) | P0–P5 实施顺序与阶段验收 |
| [汇报规划](docs/PRESENTATION_PLAN.md) | 面向最终方案的汇报结构与证据要求 |
| [相关工作](docs/RELATED_WORK.md) | 既有参考文献入口与后续核验范围 |
| [开发说明](DEVELOPMENT.md) | 实际环境、依赖与验证命令 |
| [Agent 约束](AGENTS.md) | 实现必须遵守的边界 |

## 设计依据

[项目计划书 V4](docs/EvoTeam_项目计划书_V4_概念冻结与架构闭环版.docx) 是项目申请材料；[飞书讨论结果](docs/飞书讨论结果/) 保留原始讨论。现行文档以 v2/v3 最终结论与 V4 计划书统一后的基线为准。原始记录中的早期方案、示例数字与示意代码不能直接作为实现要求；来源映射见 [决策](docs/DECISIONS.md)。

## 技术基线

Python 3.12、uv、Pydantic、openJiuwen Core。后端相关依赖已经声明；前端选型与开工安排见开发说明。EvoTeam 自己维护领域对象，只有 Runtime Adapter 直接依赖 openJiuwen SDK。

```bash
uv sync
uv run python --version
```

完整开发与检查方式见 [DEVELOPMENT.md](DEVELOPMENT.md)。
