# EvoTeam 开发说明

## 当前仓库状态

已有 Python 项目、uv.lock、.python-version 与依赖声明；`main.py` 只打印占位信息。尚无 EvoTeam 业务包、测试套件、服务入口或前端工程。安装依赖不代表架构模块已实现。

开发前阅读 README、AGENTS、PROJECT、ARCHITECTURE、ROADMAP；演进和评价工作同时阅读 EXPERIMENTS、DECISIONS。产品与架构按最终讨论冻结，先完成文档统一，再按 P0–P5 实现。

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
| 后端相关依赖 | 已声明 FastAPI、Uvicorn、HTTPX、SSE、Pydantic Settings，尚无服务实现 |
| 持久化相关依赖 | 已声明 SQLAlchemy、Alembic；首轮按单机 SQLite 路径实现 |
| 前端 | React + TypeScript 仍为候选，仓库没有前端工程；具体组件在 P5 确定 |
| 检查工具 | 已声明 pytest、pytest-asyncio、Ruff、Pyright；专项配置和测试需在 P0 补齐 |

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

当前没有测试套件时，pytest 的 “no tests ran” 不代表通过。必须在汇报中说明缺失，不为文档改动编造测试结果。业务实现开始后，补齐必要配置并运行全部相关检查。

## Git 与文件管理

初始化阶段可直接完善 main 文档和基础骨架。正式功能开发使用任务分支和 PR；遵循任务约定，不建立每人永久分支。

提交 pyproject.toml、uv.lock、.python-version、源码、测试、版本化配置和文档。创建环境样例时仅保存字段和占位值，不包含凭据。虚拟环境、真实 .env、运行数据库、缓存和系统文件不纳入版本管理；当前仓库尚需在工程基线阶段补齐 .gitignore / .env.example。

飞书讨论与项目计划书作为原始设计依据保留。实现规范只有 README 导航中的主题文档，不再新增平行 v1/v2/v3 草案。每次实现同步更新真实进度和可执行命令，不把计划写成已完成能力。
