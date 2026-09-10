# 任务书 A：核心后端、数据与实验

## 给组员及其 Codex 的身份说明

**被指派阅读并执行本文件，即承担“执行者 A：核心开发”的职责。** A 是固定的任务代号，不是姓名。无论是谁把本文件交给 Codex，都不能由“当前聊天用户”推断其为项目总负责人。

“项目负责人”指分配这两份任务书并验收成果的人，只负责审查与确认，不承担本任务的编码、数据集制作、实验脚本或报告初稿。执行者 A 及其 Codex 必须把这些交付准备完整，不能让负责人补做。

本轮范围：**A0 + N1–N4**。执行者 B 的前端、展示 API、导出和 PPT 不属于 A。后续完整项目任务见 ROADMAP，但不能据此自动扩展本轮范围。

### 可直接交给 Codex 的开工指令

> 请以“执行者 A：核心开发”的身份执行 docs/TASK_CORE.md。遵守仓库 AGENTS.md，先核对 main 的实际实现和本任务清单，只开发本文件分配的 A0、N1–N4。完整承担数据准备、验证代码、实验脚本与报告；项目负责人只审查，不要求其并行编码。不要开发 TASK_PRESENTATION.md 的内容。先完成 A0 并交付，再按 N1→N2→N3→N4 推进；依赖或实验授权缺失时明确报告，并继续本侧不受阻的工作。每个可验收交付列出文件、接口、测试和限制，由项目负责人验收后统一纳入 main，不自行合并或修改另一侧模块。

## 1. 开工依据与文件边界

先读 README、DEVELOPMENT、AGENTS、PROJECT、ARCHITECTURE、ROADMAP；本任务必须同时读 EXPERIMENTS、DECISIONS。字段和文件名以下述计划为约定，开工时检查是否已被前序 PR 实现，不能重复造实现。

| A 可修改 | A 不接管 |
| --- | --- |
| `evoteam/domain/`、`evolution/`、`monitoring/`、`orchestration/`、`storage/`、`runtime/`、`entrypoints.py`、`cli.py`，限本任务所需 | `frontend/`、`evoteam/presentation/`、`evoteam/api_queries.py`、展示页面和PPT制作 |
| 核心/隔离/配对/迁移测试、实验数据、实验配置和脱敏结果报告 | B维护的展示Schema、fixture和截图，不自行复制成第二套 |
| 本文件进度、EXPERIMENTS、与核心实现有关的DEVELOPMENT说明 | 总计划的负责人安排、另一份任务书的任务范围 |

`evoteam/api.py` 中挂载只读 router 由 B 实现，不留给项目负责人写集成代码。A 如果发现需要修改 API 写操作，先说明原因并与 B 对齐改动范围，不同时改同一文件。展示层发现缺字段由 A 补领域或存储实现，B 负责消费。

Python 正式依赖使用 uv；SDK 依赖只进入 Adapter。禁止改变 Role Pool、单条版本链、实验隔离和 Gate 权限边界。

## 2. A0：先交付 B 所需的只读存储能力

A0 是并行开发的第一个交接点，可在新临时数据库上实现，不必等真实实验。目标是让 B 有稳定的查询入口；A 不负责 HTTP/前端包装。

**文件：** `evoteam/storage/protocol.py`、`evoteam/storage/sqlite.py`；新测试 `tests/test_read_queries.py`。已有 `read_snapshot`、`events_for_run`、`get_record`、`get_proposal`、`get_attribution`、`get_validation` 继续复用。

拟新增的 Python 端口（若已有等价端口，保留兼容实现并在交付中给出映射）：

```python
# RunStore
async def get_sealed_run(run_id: str) -> SealedRun: ...
async def list_runs(
    strategy_id: str, *, purpose: RunPurpose | None, limit: int, cursor: str | None
) -> tuple[tuple[SealedRun, ...], str | None]: ...
# StrategyStore
async def list_versions(strategy_id: str) -> tuple[Strategy, ...]: ...
# EvolutionStore
async def list_records(
    strategy_id: str, *, limit: int, cursor: str | None
) -> tuple[tuple[EvolutionRecord, ...], str | None]: ...
```

- [x] 先测试缺失 ID 的明确查找失败、空列表、跨策略/用途隔离、分页稳定性、非法 limit/cursor、读取不产生写入。
- [x] 用稳定排序和不透明 cursor 实现分页；Run 按 sealed_at/run_id，版本按 version；Evolution 使用确定的排序键并写明。cursor须绑定过滤条件，不在不同查询间混用。
- [x] 缺失单条记录统一为 KeyError；旧数据缺少字段保持 None，不推断时间、成本或晋级历史。不得返回模型凭据。
- [x] 跑 `uv run pytest tests/test_read_queries.py -q` 及完整检查。
- [ ] 交付接口签名、排序/错误行为、测试结果和示例调用；通过验收纳入 main 后把提交号发给 B。不要要求负责人自己补端口。

**交接验收：** B能通过端口取得列表、封存索引及已有详细证据，不需读SQL或等待N4。A0与N1都改sqlite.py，由A顺序处理，不并行编辑同一文件。

## 3. N1–N4 执行要求

以下每项的主责都为 A，不再分给项目负责人。
## N1：给已有数据库提供显式升级入口

**文件：** 新建 `evoteam/storage/migrations.py`、`tests/test_migrations.py`；修改 `evoteam/cli.py`、`evoteam/storage/sqlite.py`、`DEVELOPMENT.md`。

**接口约定：** `upgrade_database(database: Path, *, backup: Path) -> None`；CLI 为 `python -m evoteam migrate --database <已有库> --backup <新备份路径>`。只针对已识别的六表基础版本、组员十一表版本和当前十二表版本；未知布局拒绝。

- [x] 写回归测试：使用旧表布局创建库并保存固定策略、事件和封存记录；升级后原记录逐字段不变，新增表可用；二次升级不改证据。
- [x] 覆盖错误路径：备份路径已存在、数据库缺失、未知列结构、备份失败时不得执行迁移；失败不能留下半升级状态。
- [x] 执行 `uv run pytest tests/test_migrations.py -q`，确认新行为尚未实现导致失败。
- [x] 使用 SQLite backup API 生成一致备份，显式识别布局，事务补齐缺失表并保存 Schema 版本；不得重建或清空运行表。升级期间要求停止写入，CLI 检查成功后再开放服务。
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

- [x] 添加以下身份改名不能逃过检查的测试，以及空分区、重复 ID、同引用内容变更的失败测试。

```python
renamed = task.model_copy(update={"task_id": "new-id"}, deep=True)
assert task_fingerprint(task) == task_fingerprint(renamed)
with pytest.raises(ValueError, match="跨分区"):
    validate_partitions({"history": [task], "validation": [renamed], "final_test": [other]})
```

- [x] 执行 `uv run pytest tests/test_dataset_isolation.py -q`，观察失败。
- [x] 摘要使用 task_type、input_schema、inputs 的规范 JSON：键排序、固定分隔符、UTF-8、SHA-256；排除 task_id 和 instruction，使仅换 ID 或改写指令不能复用同一结构化题目。此规则用于检测内容重复，不声称能检测所有同构题目。
- [x] 验证器加载题目前校验分区和摘要；Manager 在候选生成前只验证历史来源，候选生成器仍只接归因和策略，不能得到验证题目或答案。Final Test 禁止作为 ValidationPlan 的数据集引用。
- [x] 注册资源冲突、依赖、期限、技能、预算、合法不可行输入等子类；每条题目有独立 ID、内容与人工复核记录。用例数量依覆盖需要确定，正式实验样本量由 N4 预注册。
- [ ] 执行隔离回归、原 Validator 与治理测试，更新实验协议并提交独立 PR。

**验收：** 换 ID、换 instruction 或重排 JSON 键不能把同题混入不同分区；未登记、摘要不符和 Final Test 引用在模型调用前拒绝。历史运行必须能反查数据清单版本。

## N3：保留逐任务配对结果，避免汇总掩盖退化

**文件：** 修改 `evoteam/domain/evolution.py`、`evoteam/evolution/validator.py`、`evoteam/evolution/gate.py`、`evoteam/evolution/attribution.py`；新建 `tests/test_validation_pairs.py`、`tests/test_gate_regressions.py`。

**接口约定：** 增加不可变 `ValidationPair`，字段为 task_id、task_fingerprint、subclass、repeat_index、current_run_id、candidate_run_id、current_metrics、candidate_metrics；`ValidationResult.pairs` 保存有序 tuple。旧汇总字段保留兼容；旧记录缺少 pairs 时不能冒充完整配对证据。

- [x] 构造两道题的真实封存验证：候选在第一题改善、第二题从成功退化为失败，整体错误总数仍下降。测试 Gate 不得仅因总错误下降而 PASS。
- [x] 测试重复执行同一道题不会增加独立任务数；失败/超时计入分母，缺失用量保持 None，取消终止批次。
- [x] 执行 `uv run pytest tests/test_validation_pairs.py tests/test_gate_regressions.py -q`，观察失败。
- [x] Validator 每完成一对封存运行就构造 ValidationPair，并由同一配对序列计算汇总，保存成功数/总数、独立题目数、每个子类的表现和延迟分布。P95 注明算法与样本数，样本不足不下稳定性结论。
- [x] Gate 增加显式预注册的独立任务门槛与子类退化约束；未登记或旧记录没有所需证据时继续采样。使用测试专用规则验证边界，不把测试数值写成正式默认参数。
- [x] 保存实际采样配置；在 Runtime 尚未支持 seed 时继续记录 seed_not_applied。相同标签不等于相同随机过程，不能为通过验收而移除此限制。
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
- [x] 先在 History 分区运行固定 v0，报告每类任务成功率、错误类型、Token、耗时、超时和返工次数。样本不足时补充数据，不直接降低 Gate。
- [ ] 根据基线波动登记新的 Monitor/Gate Policy 版本：窗口、触发、冷却、独立任务数、重复数、收益和成本边界、候选选择及验证复用次数。由团队复核后冻结。
- [ ] 按固定协议比较 Current、Prompt Candidate 和 Verifier Candidate；每个候选保存直接证据、差异、完整 Validation 和 Gate。全部 Reject 是有效结果。
- [ ] 只有候选通过冻结规则才晋级；用未参与选择的未来任务和 Final Test 检查效果。最终测试不用于反复选候选或改门槛。
- [ ] 报告线上与离线总成本、失败候选、收益不确定性，以及是否观察到真实的版本变化和后续影响。

**验收：** 他人可以从代码提交、配置和数据摘要复现运行流程，并核对结果；不要求随机模型逐字复现。未获得真实收益时如实记录，不预设必须晋级。


## 4. N2、N4 中项目负责人具体做什么

| 环节 | A必须准备 | 项目负责人只做 |
| --- | --- | --- |
| N2数据 | 题目、分区清单、可行/不可行标记、去重测试、抽查说明 | 检查分区规则，抽查题目与来源；接受或退回 |
| N3实现 | 配对Schema、兼容行为、Gate测试、对外字段说明 | 检查是否满足验收，确认跨侧接口变化 |
| N4运行前 | 实验命令、代码/数据版本、模型配置、预算/调用上限、Policy草案和限制 | 确认实验范围、费用上限与预注册口径；不写脚本 |
| N4运行后 | 原始可追溯记录、统计、失败案例、结论初稿、复现说明 | 核对结果与结论，接受或要求补证据 |

实验分两次确认：先批准固定v0基线的范围和费用，再根据基线冻结候选比较规则。已明确批准的同一范围不重复征求批准；缺少凭据/预算授权时先交付本地测试、dry-run统计和完整命令，等待确认后执行外部调用。不得一边看验证答案一边改阈值。

Final Test 在规则和候选冻结后使用；即使A制作数据，也不得将其答案交给CandidateGenerator或用来反复调整候选。

## 5. 与 B 的依赖和阻塞处理

- **立即可做：** A0、N1；准备N2数据和校验测试。B可同时做展示fixture、页面和PPT。
- **A交付给B：** A0端口；N1升级命令；N3新增配对字段及兼容说明；N4可共享Run/Evolution ID、完整记录可用性和结果报告。
- **B交付给A：** B0消费Schema与缺字段清单；B3真实库联调报告。B不决定统计/Gate语义，A不为页面美观伪造字段。
- **接口没合入main：** 明确列出依赖ID及生产方；不要求负责人写适配代码。A继续本侧其他任务，B继续fixture页面/PPT。
- **字段变更：** A给出兼容方案和示例，B更新消费测试；主责各自修复自己的代码。负责人检查，不做第三份实现。
- **交接方式：** 报告中使用“交付内容＋测试结果＋main提交号＋缺失项”，组员各自Codex只依据已可读取证据行动，不假设能看到另一聊天上下文。

## 6. 完成与停止边界

- [ ] A0、N1–N3均有可复现测试；N2题目与数据清单由A制作完成。
- [ ] N4已有经确认的实验结果，或明确标注因何等待授权/凭据，准备工作不能留给负责人。
- [ ] B需要的端口与字段已交付，错误/空值行为可测试。
- [ ] 更新本任务书勾选状态，不替B标记完成；后续Tool/自动治理等不在本次自动开工范围。

执行 `uv sync`、`uv run pytest`、`uv run ruff check .`、`uv run ruff format --check .`、`uv run pyright`。不提交密钥、运行数据库和SDK日志。每次交付按AGENTS汇报，并额外列出“提供给B的接口/证据”和“需要项目负责人确认的事项”。

团队阅读与成果入口始终为main。工作可在短期任务分支隔离，交付验收后合入main再同步；不能把“已push个人分支”称为团队已经收到最终成果。
