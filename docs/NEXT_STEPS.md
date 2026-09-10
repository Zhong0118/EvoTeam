# EvoTeam 下一轮实施计划

> 执行说明：按任务逐项使用 `superpowers:executing-plans`；每项先补失败测试，再实现和复核。以下代码和文件名是下一轮实现约定，不表示已有功能。

**目标：** 让现有受限演进原型具备可升级的存储、可审计的数据分区和逐任务验证证据，为真实基线校准做好准备。

**架构：** 沿用单条 Strategy 版本链、固定 Role Pool、openJiuwen Adapter 和独立 Evaluator。数据登记负责隔离，Validator 负责实验，Gate 负责裁决；不合并这些职责。

**技术：** Python 3.12、uv、Pydantic、SQLAlchemy / SQLite、openJiuwen Core；不增加框架或服务。

**依据：** [PROJECT](PROJECT.md)、[ARCHITECTURE](ARCHITECTURE.md)、[EXPERIMENTS](EXPERIMENTS.md)、[本轮审查](VERSION_COMPARISON.md)。长期 P0–P5 阶段定义继续以 [ROADMAP](ROADMAP.md) 为准。

## 起点与交付边界

当前已有在线运行、Prompt/Verifier 候选、基本 Gate、版本治理和重复触发保护。仍缺数据库升级入口、任务内容隔离、逐任务负迁移与充分样本的真实效果证据。本计划前三项为工程任务，第四项为数据和实验任务；都不预设候选一定晋级。

| 顺序 | 建议负责方向 | 交付物 | 前置依赖 |
| --- | --- | --- | --- |
| N1 | Runtime / Storage | 显式数据库升级命令与恢复说明 | 当前 main |
| N2 | Domain / Experiment | 版本化分区清单与内容重复检查 | 可与 N1 并行；集成后使用升级后的库 |
| N3 | Evaluation / Experiment | 逐任务配对指标与退化检查 | N2 |
| N4 | 团队共同确认实验协议 | 固定基线、冻结 Policy、真实对照报告 | N1–N3 |

人员由团队分配。每项独立任务分支、PR 和测试，不直接在 main 累积功能修改。

## N1：给已有数据库提供显式升级入口

**文件：** 新建 `evoteam/storage/migrations.py`、`tests/test_migrations.py`；修改 `evoteam/cli.py`、`evoteam/storage/sqlite.py`、`DEVELOPMENT.md`。

**接口约定：** `upgrade_database(database: Path, *, backup: Path) -> None`；CLI 为 `python -m evoteam migrate --database <已有库> --backup <新备份路径>`。只针对已识别的六表基础版本、组员十一表版本和当前十二表版本；未知布局拒绝。

- [ ] 写回归测试：使用旧表布局创建库并保存固定策略、事件和封存记录；升级后原记录逐字段不变，新增表可用；二次升级不改证据。
- [ ] 覆盖错误路径：备份路径已存在、数据库缺失、未知列结构、备份失败时不得执行迁移；失败不能留下半升级状态。
- [ ] 执行 `uv run pytest tests/test_migrations.py -q`，确认新行为尚未实现导致失败。
- [ ] 使用 SQLite backup API 生成一致备份，显式识别布局，事务补齐缺失表并保存 Schema 版本；不得重建或清空运行表。升级期间要求停止写入，CLI 检查成功后再开放服务。
- [ ] 执行测试和全仓检查，更新升级命令及恢复说明，提交独立 PR。

目标调用方式：

```python
upgrade_database(database, backup=backup)
ports = await SQLiteStorage(f"sqlite:///{database}").open()
assert await ports.runs.read_snapshot(run_id) == original_snapshot
```

**验收：** 老库可用明确命令升级，已有 Run / Strategy / Prompt 引用不变。活动 evolution claim 不自动清除；硬退出恢复另立任务，防止迁移变成重复付费的入口。

## N2：登记并校验 History / Validation / Final Test

**文件：** 新建 `evoteam/domain/dataset.py`、`tests/test_dataset_isolation.py`、`examples/datasets/project_planning_manifest.json`；修改 `evoteam/evolution/datasets.py`、`evoteam/evolution/validator.py`、`evoteam/evolution/manager.py`、`docs/EXPERIMENTS.md`。

**接口约定：** `task_fingerprint(task: Task) -> str`；`validate_partitions(partitions: Mapping[str, Sequence[Task]]) -> None`，分区键固定为 `history`、`validation`、`final_test`。清单保存 AssetRef、分区、task_id、内容摘要和预先定义的任务子类。

- [ ] 添加以下身份改名不能逃过检查的测试，以及空分区、重复 ID、同引用内容变更的失败测试。

```python
renamed = task.model_copy(update={"task_id": "new-id"}, deep=True)
assert task_fingerprint(task) == task_fingerprint(renamed)
with pytest.raises(ValueError, match="跨分区"):
    validate_partitions({"history": [task], "validation": [renamed], "final_test": [other]})
```

- [ ] 执行 `uv run pytest tests/test_dataset_isolation.py -q`，观察失败。
- [ ] 摘要使用 task_type、input_schema、inputs 的规范 JSON：键排序、固定分隔符、UTF-8、SHA-256；排除 task_id 和 instruction，使仅换 ID 或改写指令不能复用同一结构化题目。此规则用于检测内容重复，不声称能检测所有同构题目。
- [ ] 验证器加载题目前校验分区和摘要；Manager 在候选生成前只验证历史来源，候选生成器仍只接归因和策略，不能得到验证题目或答案。Final Test 禁止作为 ValidationPlan 的数据集引用。
- [ ] 注册资源冲突、依赖、期限、技能、预算、合法不可行输入等子类；每条题目有独立 ID、内容与人工复核记录。用例数量依覆盖需要确定，正式实验样本量由 N4 预注册。
- [ ] 执行隔离回归、原 Validator 与治理测试，更新实验协议并提交独立 PR。

**验收：** 换 ID、换 instruction 或重排 JSON 键不能把同题混入不同分区；未登记、摘要不符和 Final Test 引用在模型调用前拒绝。历史运行必须能反查数据清单版本。

## N3：保留逐任务配对结果，避免汇总掩盖退化

**文件：** 修改 `evoteam/domain/evolution.py`、`evoteam/evolution/validator.py`、`evoteam/evolution/gate.py`、`evoteam/evolution/attribution.py`；新建 `tests/test_validation_pairs.py`、`tests/test_gate_regressions.py`。

**接口约定：** 增加不可变 `ValidationPair`，字段为 task_id、task_fingerprint、subclass、repeat_index、current_run_id、candidate_run_id、current_metrics、candidate_metrics；`ValidationResult.pairs` 保存有序 tuple。旧汇总字段保留兼容；旧记录缺少 pairs 时不能冒充完整配对证据。

- [ ] 构造两道题的真实封存验证：候选在第一题改善、第二题从成功退化为失败，整体错误总数仍下降。测试 Gate 不得仅因总错误下降而 PASS。
- [ ] 测试重复执行同一道题不会增加独立任务数；失败/超时计入分母，缺失用量保持 None，取消终止批次。
- [ ] 执行 `uv run pytest tests/test_validation_pairs.py tests/test_gate_regressions.py -q`，观察失败。
- [ ] Validator 每完成一对封存运行就构造 ValidationPair，并由同一配对序列计算汇总，保存成功数/总数、独立题目数、每个子类的表现和延迟分布。P95 注明算法与样本数，样本不足不下稳定性结论。
- [ ] Gate 增加显式预注册的独立任务门槛与子类退化约束；未登记或旧记录没有所需证据时继续采样。使用测试专用规则验证边界，不把测试数值写成正式默认参数。
- [ ] 保存实际采样配置；在 Runtime 尚未支持 seed 时继续记录 seed_not_applied。相同标签不等于相同随机过程，不能为通过验收而移除此限制。
- [ ] 执行配对、Gate、治理和 SDK 回归，更新运行指南并提交独立 PR。

数据形状：

```python
assert len(result.pairs) == len(result.current_run_ids)
assert {p.task_fingerprint for p in result.pairs} == registered_task_fingerprints
assert all(p.current_run_id != p.candidate_run_id for p in result.pairs)
```

**验收：** 任一 Gate 决定能下钻到题目、重复次序、两条 Run 和指标；单题重复与独立题目不混计。改进归因只陈述受当前对照支持的结果。

## N4：固定真实基线，再做候选比较

**产物：** 更新 `docs/EXPERIMENTS.md` 的有效协议；配置保存在 `examples/experiments/`，脱敏报告保存在 `runs/<experiment_id>/`，数据库、日志和密钥不入 Git。

- [ ] 使用 N2 清单，在调用模型前登记代码提交、数据摘要、模型/Prompt/评价器版本、预算、温度和 top_p，以及请求次数上限；有效凭据仅留本地环境。
- [ ] 先在 History 分区运行固定 v0，报告每类任务成功率、错误类型、Token、耗时、超时和返工次数。样本不足时补充数据，不直接降低 Gate。
- [ ] 根据基线波动登记新的 Monitor/Gate Policy 版本：窗口、触发、冷却、独立任务数、重复数、收益和成本边界、候选选择及验证复用次数。由团队复核后冻结。
- [ ] 按固定协议比较 Current、Prompt Candidate 和 Verifier Candidate；每个候选保存直接证据、差异、完整 Validation 和 Gate。全部 Reject 是有效结果。
- [ ] 只有候选通过冻结规则才晋级；用未参与选择的未来任务和 Final Test 检查效果。最终测试不用于反复选候选或改门槛。
- [ ] 报告线上与离线总成本、失败候选、收益不确定性，以及是否观察到真实的版本变化和后续影响。

**验收：** 他人可以从代码提交、配置和数据摘要复现运行流程，并核对结果；不要求随机模型逐字复现。未获得真实收益时如实记录，不预设必须晋级。

## 之后再推进

N4 之后按路线图推进受控 constraint_checker Tool Policy、贡献消融、自动 Stable/Reopen/Rollback 规则、活动 claim 恢复，以及只读证据展示。报告生成和数据分析的补充套件放在主场景实验机制稳定后。新增实现不得扩大 Role、工具权限或引入 Strategy Family。

## 每个 PR 的统一完成条件

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

测试通过、规范与实现一致、错误路径留证据、无凭据与运行数据库进入 Git。每完成一项更新本文件复选框和路线图实际进度，避免另建冲突版本。
