# EvoTeam 实验与评价协议

实验要验证：跨任务证据是否帮助系统改对 Strategy，以及经过独立验证的变化是否改善未来任务，在质量、成本、稳定性之间取得可解释的收益。固定 v0、运行时动态适配与跨任务演进必须分别测量。

仓库保留了组员提交的少量真实调用与 Gate Reject 回归记录，尚未取得充分样本支持的真实晋级收益结论。本文件中的流程与指标是实验规范；数值门槛需在 V0 baseline 校准后预注册，不能用讨论示例代替结果。

## 1. 三类任务

| 任务 | 优先级与用途 | 输入与可验证输出 | 主要指标 |
| --- | --- | --- | --- |
| 项目计划生成与校验 | 主场景，完整机制验证 | 工作项、人员、依赖、期限、预算 → 结构化计划及依据 | 硬约束满足率、计划完整性、可执行性 |
| 专题报告生成 | 较小规模适用性验证 | 固定资料包 → 带来源的报告 | 事实准确率、引用有效率、完整性 |
| 数据分析 | 较小规模 Tool Policy 验证 | 固定数据及指标口径 → 计算产物与结论 | 计算正确率、口径一致性、证据覆盖率 |

首轮使用离线资料与受控工具。每个任务套件保存输入、数据版本、评价规则和可复现记录。三类任务不代表三棵 Strategy Family，也不要求并行开发三个产品。

## 2. 数据隔离

| 分区 | 用途 | 禁止事项 |
| --- | --- | --- |
| History / Evolution Set | 跑 v0、发现模式、形成经验、归因与候选生成 | 不与最终测试混用 |
| Validation Set | Current / Candidate 配对比较、Gate、Improvement Attribution | 候选生成不得读取标准答案；不得边看答案边改候选 |
| Final Test Set | 阶段结束报告泛化与最终效果 | 不用于反复选择 Candidate 或调整阈值 |

数据划分与版本在实验开始前登记。验证结果可以形成治理证据，但不能把验证答案或反复试探同一集合变成新的隐性训练集。若需要新的候选生成轮次，应按预注册协议控制验证复用、轮次与独立评测。

### 2.1 数据清单与内容身份

项目规划清单当前为 `project-planning-manifest@2`，文件位于 `examples/datasets/project_planning_manifest.json`。N4 前将 History 扩充为两个子类各三题；Validation 和 Final Test 内容保持版本 1，不因 History 扩充而改动。三个分区分别登记为：

| 分区 | AssetRef | 当前人工复核子类 |
| --- | --- | --- |
| History | `project-planning-history@2` | `resource_conflict`、`dependency`（各 3 题） |
| Validation | `project-planning-validation@1` | `deadline`、`skill` |
| Final Test | `project-planning-final-test@1` | `budget`、`valid_infeasible` |

`valid_infeasible` 表示输入通过固定 Task/PlanningInput Schema，但不存在满足技能等硬约束的合法排期，不表示输入格式损坏。History 当前每个子类三题，只用于第一轮描述性 v0 基线；Validation 与 Final Test 每个子类仍只有一题，尚不足以支持稳定的逐子类收益结论。

### 2.2 N4 第一阶段冻结配置

第一阶段只运行 `n4-baseline-v0-history2-r1`：固定 v0、History@2 六题、一次重复、Planner/Executor/Critic 每题最多三次模型调用，总硬上限 18 次。配置位于 `examples/experiments/n4_baseline_v0.json`。候选比较和 Final Test 在本批次均关闭；不得用剩余额度顺便启动。执行入口会拒绝覆盖已有输出目录，并在调用前核对清单版本、任务数、Strategy、模型引用和请求上限。

命令如下，输出数据库不进入 Git，脱敏 `baseline_report.json` 保存代码提交、三份输入摘要、模型非秘密参数、Prompt 引用、预算、运行 ID、评价与实际请求数：

```bash
uv run python -m scripts.run_n4_baseline \
  --config examples/experiments/n4_baseline_v0.json \
  --output runs/n4-baseline-v0-history2-r1
```

任务内容摘要固定为 SHA-256：仅对 `task_type`、`input_schema`、`inputs` 做规范 JSON 编码，使用 UTF-8、键排序和固定分隔符。`task_id` 与 `instruction` 被排除，因此只改 ID、改写指令或调整 JSON 键顺序不能把同一结构化题目放进其他分区。该摘要用于发现完全相同的结构化输入，不声称能识别语义改写、数值扰动或所有同构题目。

清单加载时重新计算并核对每条摘要；未登记引用、同引用内容变化、空分区、重复 ID 和跨分区内容重复均在模型调用前拒绝。Validator 只能把 `validation` 数据集作为 `ValidationPlan.dataset_ref`，`final_test` 引用不能进入候选选择。EvolutionManager 在归因和候选生成前，通过封存 Run 的 `RunSnapshot.task` 只反查 History 登记，不加载 Validation 或 Final Test；反查结果包含 manifest、dataset、task fingerprint 与 subclass，可用于从历史 Run 追溯清单版本。CandidateGenerator 的输入仍只有 Current Strategy、Failure Attribution 和 Policy。

### 2.3 执行时来源与预检快照

新 Run 在执行前固定 `DatasetSource`，封存索引和快照保存 manifest_ref、dataset_ref、partition、task_id、fingerprint、subclass。历史校验核对已封存来源，清单升级不会改变旧 Run 身份。旧记录仍可读取，但缺来源时拒绝进入新演进，不用当前清单补造执行时身份。

真实实验在创建 Runtime 前独占保存 `preflight.json`：代码提交、输入内容与摘要、实际模型参数、完整评价器引用、Prompt 内容摘要和预算。已跟踪代码有未提交修改时拒绝开始；`expected_model` 存在时必须逐项匹配，N4 对照要求提供此字段。报告采用预检值，不在结束后重读摘要。失败/取消保存终态与已完成记录，取消不继续下一题，输出目录禁止隐式续跑。

### 2.4 N4 有限对照：已实现，真实执行待模型配置

配置为 `examples/experiments/n4_comparison_v1.json`。独立数据库中的研究对照复用正式 Orchestrator、Evaluator、Validator、Improvement Attribution 和 Gate。两个研究臂预先指定为 executor@v1-resource-check、verifier@v0，不伪造 Trigger，不称为自动演进，不修改已有服务数据库。

固定顺序：History 六题 v0 → Prompt Candidate 两题配对 → Verifier Candidate 两题配对 → 当前策略 Final Test 两题。每组一次重复，Validation 只用于这两种已确定候选。两组 Gate 保存后才读取 Final Test，不能据其结果再挑候选或调门槛。

沿用历史基线模型参数、零 Retry，最多 **50 次模型请求**：6×3 + 2×(3+3) + 2×(3+4) + 2×3。失败请求计入上限。Monitor 沿用基线规则；研究 Gate 禁止质量/子类退化，要求至少六个独立验证任务、Token 增幅最多 25%、延迟增幅最多 50%。成本和延迟边界为开发者研究约束，并非六题基线估出的统计结论。当前 Validation 两题不能满足六题门槛，不降低门槛制造 PASS；本批不晋级，只进行有限对照与服务策略最终测试。充分样本的收益校准和自动晋级仍须补数据并走既有 Manager 流程。

```bash
# 仅预检，不创建模型 Runtime；预检目录不可用于隐式续跑。
uv run python -m scripts.run_n4_campaign --config examples/experiments/n4_comparison_v1.json --env-file /absolute/path/to/local.env --output runs/n4-preflight-v1 --preflight-only

# 真实执行使用新目录，需要可用的本地模型配置。
uv run python -m scripts.run_n4_campaign --config examples/experiments/n4_comparison_v1.json --env-file /absolute/path/to/local.env --output runs/n4-fixed-comparison-v1
```

`campaign_report.json` 保存冻结身份、候选配置、逐题配对、改进归因、Gate、服务版本前后、Final Test ID、脱敏快照和事件。`metrics_by_purpose` 分开报告线上基线、离线验证及最终测试的成功数/总数、Token、实例数、Retry、工具数和延迟；未知值保留，另列已知小计。费用未知时不换算金额，失败/超时/取消均保留。

当前端到端离线测试已覆盖这条路径、重复执行、取消和预算拒绝，尚无本批真实报告。旧 `n4-baseline-v0-history2-r1` 是历史结果，不能冒充修复后重跑。模型配置与真实结果未就绪前，N4 不标全部完成。

## 3. 对照与消融

| 方案 | 设置 | 回答的问题 |
| --- | --- | --- |
| Single Agent | 一个 Agent 完成任务 | 多角色协作是否有收益 |
| Fixed Multi-Agent | 固定 Planner → Executor → Critic，无跨任务更新 | 固定组织基线 |
| Retry / Reflection | 只在同一任务中返工，Strategy 不变 | 单次补救是否已足够 |
| Task-Adaptive Team without History | 按 TaskProfile 选择既有配置，无历史经验、无策略更新 | 运行时组队与跨任务演进的收益是否混淆 |
| Prompt Mutation | 只更新 AgentConfig Prompt | 模板改动贡献 |
| Tool Policy Mutation | 只更新已授权工具的使用策略 | 确定性工具贡献 |
| Structure Mutation | AgentConfig 增删、Rewire、Conditionalize | 组织结构变化是否有效 |
| Full EvoTeam | Trigger、Attribution、Bounded Mutation、Validation、Lifecycle | 完整机制的收益与治理成本 |

各方案尽量共享模型、任务、工具能力、评价协议和最大预算。不同方案实际耗用的 Token、次数、延迟与 Agent 数必须如实报告。Full EvoTeam 的离线候选生成与验证成本单独列出，不能只展示上线后的节省。

## 4. 单 Run 评价

Evaluator 在 Team 外评分，Critic / Verifier 负责任务内质量控制。优先程序化检查硬约束，再使用固定 Rubric / Judge 补充语义维度。

项目计划评价至少覆盖：必需工作项、依赖合法性及执行顺序、人员/资源重叠、期限、预算、风险与交付完整性。具体时间单位、重叠区间、资源容量和约束权重需在 Task / Constraint Schema 中定义。

Run 记录质量、成功状态、错误类型与严重程度、Token、工具次数、延迟、Agent 数、通信及 Retry。缺失用量必须标记未知，不能记为零；失败、超时和取消保留在统计口径内，按预注册规则处理。

## 5. Monitor 与停止实验

开发者先定义 Trigger 类型，再使用 v0 正常波动校准参数。LLM 不修改阈值。窗口大小是检查周期，不是强制演进周期。

至少验证以下行为：

- 样本不足：继续积累，不生成 Candidate。
- 稳定窗口：维持当前版本，可进入 STABLE，主动候选数为零。
- 重复失败或明显退化：达到阈值时产生对应证据的 Trigger。
- 高成本或低贡献：有可比较证据才触发效率优化。
- 冷却期间：不重复消费同一问题造成策略频繁切换。
- Stable 后出现新错误、分布或能力环境变化：达到条件才 Reopen。
- 晋级后退化：正确回滚并保留失败版本及恢复目标。

检验 False Trigger Rate、Trigger Precision、Stable Duration、Reopen Rate、Rollback Rate 与 Strategy Thrashing 次数。基准中的异常注入时点和预期行为应独立记录。

## 6. Attribution Benchmark

归因准确率必须有 ground truth。通过可程序验证错误、人工注入故障和少量人工标注构建样本，预先记录错误注入点与应承担控制责任的节点。

| 归因 | 时点 | 证据与评测 |
| --- | --- | --- |
| Failure Attribution | Candidate 前 | 用 Trace 与检查器定位 Origin、Control，对照已知故障点 |
| Contribution Analysis | 跨 Run 分析 | 节点、Tool、Edge 消融或反事实比较，检查移除后质量与成本变化 |
| Improvement Attribution | 验证后晋级前 | 将收益对应到目标 Mutation，检查单因素对照与适用子类 |

资源冲突示例：Executor 产生重叠排期是 Origin，Critic 未检查出冲突是 Control。不能只因最终输出来自 Executor 就把所有错误都归给它。归因低置信度时补充证据，高影响或结构性修改优先做反事实/消融。

## 7. Candidate 与公平比较

每个候选尽量只修改一个核心因素。先通过结构、引用、权限、循环和预算检查，再执行必要的 Smoke Test，最后进入独立比较；预筛选不能替代正式 Gate。

Validator 使用相同的验证任务、模型与 Tool 实现版本、随机参数、评价器、最大预算调用 Orchestrator + Evaluator。被测试的 Tool Policy 本身可以不同，但不能通过给候选额外工具能力或权限制造优势。

有随机性的实验进行多次配对重复，保存种子或可控随机参数；模型服务不支持完全确定性时记录限制并报告波动。比较均值、方差、失败分布与 P50/P95 延迟，检查收益是否跨样本/种子成立。

验证 Run 显式标记用途，与线上监控样本隔离，不能递归触发新的演进。多个候选使用独立身份，所有拒绝与失败同样留档。

## 8. Validation Gate

验证按 `(repeat_index, manifest task order)` 顺序封存 Current/Candidate，并写入不可变 `ValidationPair`；所有汇总均从同一 pair 序列计算。独立任务按 `task_fingerprint` 去重，失败和超时进入成功率分母，未知用量保持 `None`。旧记录缺少 `pairs` 时只能继续采样，不能授权晋级。

延迟分布采用 nearest-rank（升序后索引 `ceil(p*n)-1`）并保存样本数。少于 20 个已知延迟样本的 p95 只作描述性记录，带 `latency_p95_unstable_small_sample`，不作稳定性结论。Runtime 尚未消费 seed，因此实际采样配置保存 `seed_applied=false` 与 `seed_not_applied`。

Gate Policy 必须显式登记配对数、独立任务数和子类成功率退化边界。逐任务成功退化或硬约束错误增加不能被总体改善覆盖。这些字段没有正式默认阈值；示例数字仅用于测试，正式值须在 N4 基线后冻结。

| 维度 | 判定原则 | 未满足时 |
| --- | --- | --- |
| 严重错误 | 不引入新的高严重度错误 | Reject |
| 核心质量 | 不低于预注册质量底线；质量型候选达到最低收益 | Reject 或继续采样 |
| 效率收益 | 效率型候选在质量不退化前提下显著降低成本、延迟或复杂度 | Reject |
| 稳定性 | 收益不能仅来自单个样本或种子 | 继续采样或 Reject |
| 成本 | Token、工具与 P95 Latency 在边界内，计入比较所需成本 | Reject 或收窄范围后重验 |
| 泛化 | 预定义子类无不可接受的负迁移 | 收窄范围后重验或 Reject |
| 归因一致性 | 收益与目标 Mutation 有合理证据对应 | 补充归因或 Reject |

质量型与效率型收益都必须遵守质量和安全底线。不得事后调整综合分数权重来让某个候选通过；门槛、置信规则、平局处理、验证预算及候选选择规则均预注册。数据不足不能当作 PASS。

Gate 裁决与版本切换分开：Gate 给决定与理由，EvolutionManager 执行已授权生命周期操作。

## 9. 主演进案例

本节是机制案例，不是已取得的实验结果。

1. 固定 v0 在多个项目规划任务中反复发生资源冲突。
2. Evaluator 给出错误位置与指标，SealedRun 保存完整证据。
3. Monitor 检测重复模式并产生 Trigger。
4. Failure Attribution 定位 Executor 的资源安排和 Critic 的漏检。
5. Candidate A 更新 Executor Prompt，要求显式资源占用矩阵。
6. Candidate B 更新 Tool Policy，要求使用既有 constraint_checker。
7. Candidate C 引用 Verifier Role，加入 ResourceConflictVerifierConfig 及必要连接。
8. Validator 对 Current、A、B、C 做独立配对比较；Improvement Attribution 解释收益来源。
9. 按 Gate 选择有证据且成本合适的候选，或全部拒绝。
10. 晋级后在后续任务/Final Test 验证影响；稳定时停止搜索，退化时回滚。

不能预先规定“增加 Verifier 必须胜出”。若 Tool Policy 同样有效且更便宜，应按证据选择；同时结构消融必须回答组织变化是否提供独立价值。裁剪和条件启用案例用于检验更少节点是否足够。

## 10. 指标与报告

| 指标组 | 内容 |
| --- | --- |
| 任务质量 | 成功率、硬约束满足率、事实/计算正确率、完整性 |
| 运行成本 | Token、工具次数、费用（如可得）、P50/P95 Latency、Agent 数、Retry |
| 演进质量 | Trigger Precision、候选有效率、晋级率、退化率、回滚率 |
| 归因质量 | Origin / Control 命中率、改进归因一致性 |
| 组织效率 | 边数、通信轮次、节点边际贡献、条件启用命中率 |
| 迁移表现 | 预定义子类收益、负迁移率 |
| 生命周期 | False Trigger Rate、Reopen Rate、Stable Duration、版本反复切换次数 |
| 可解释性 | 证据链完整率、Diff 可追踪率 |

每项比例指标保存分母、样本量与失败处理规则；延迟分位数注明样本量，样本过少时不作稳定性结论。

实验产物应包含任务分区版本、代码提交、模型与工具版本、Prompt / AgentConfig / Strategy 快照、Policy、原始 Run、Trace、归因、候选差异、验证结果、Gate 决定和演进成本。最终展示 Before / After、消融、错误分布、质量与成本、版本及稳定时间线。
