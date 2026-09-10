# 任务书 B：展示接口、前端与 PPT

## 给组员及其 Codex 的身份说明

**被指派阅读并执行本文件，即承担“执行者 B：展示开发”的职责。** B是固定任务代号，不是姓名。不得因为当前聊天用户给出了任务，就将其认定为项目总负责人。

当前前端由项目负责人及其 Codex 接手，B 继续表示展示任务范围，不再表示原组员身份。前端和只读查询由当前开发任务完成；PPT 制作仍按原计划单独执行。

本轮范围：**B0–B4**。核心A0、N1–N4属于执行者A，缺少核心依赖不代表B获得修改核心模块的授权。本文件、FRONTEND_SPEC与PRESENTATION_PLAN共同确定B的工作，不必从总计划猜测职责。

### 当前交付状态

B0/B1 首版四类页面、六类只读查询、Run 脱敏导出、配置差异、Trace 回放已实现，启动见 [frontend/README](../frontend/README.md)。真实 SQLite/HTTP 联调使用独立无模型演示库验证；`frontend/screenshots/` 是开发样例截图，不是 N4 真实实验素材。

下一步：用团队批准的完整实测数据库做 B3 素材核对，补 Evolution 引用闭包导出与历史离线包适配；B4 PPT 未在本次前端开发中制作。A 的 N4 模型实验仍按 TASK_CORE 执行。以下待办保留作为整体 B0–B4 验收清单，不代表应重建已有页面。

### 可直接交给 Codex 的开工指令

> 请先阅读 frontend/README.md 和 docs/FRONTEND_SPEC.md，在已有四类页面、DTO 和只读 API 上继续开发，不重建工程。优先用获准共享的完整实测数据库完成 B3 核对，补充 Evolution 脱敏闭包导出及历史离线包。保留来源标签、未知指标和缺失证据，不触发模型或修改 Gate。PPT 仅在明确分配 B4 时按 PRESENTATION_PLAN 制作。不得接管 TASK_CORE；如需合并，先完成验证再由负责人决定。

## 1. 开工依据与文件边界

先读README、DEVELOPMENT、AGENTS、PROJECT、ARCHITECTURE、ROADMAP及 [前端规范](FRONTEND_SPEC.md)；展示评价/实验内容时读EXPERIMENTS和DECISIONS；逐页设计以 [PRESENTATION_PLAN](PRESENTATION_PLAN.md) 为准。

| B可修改 | B不得接管 |
| --- | --- |
| `frontend/`、`evoteam/presentation/`、`evoteam/api_queries.py`，以及展示测试 | `domain/`、`evolution/`、`orchestration/`、`monitoring/`、`storage/` 的领域/存储实现和统计规则 |
| `evoteam/api.py`中挂载只读router的最小改动，保持现有POST接口兼容 | 修改现有执行/晋级/回滚业务行为；展示侧不能直接写SQL或触发模型 |
| PPT、截图、素材来源清单、导出说明和本任务进度 | A的实验数据制作、基线调用、Gate参数校准 |

前端选型确定为 React + TypeScript + Vite、Tailwind CSS v4、shadcn/ui（Radix），图形使用 React Flow / Recharts，npm 管理锁定依赖；完整工程、样式、操作及动画约定见 [FRONTEND_SPEC](FRONTEND_SPEC.md)。这些依赖已安装并锁定，具体版本见 frontend/package-lock.json。B负责自己的接口适配与router挂载，负责人不承担集成编码。

## 2. B0：固定展示Schema与样例，立即开始

现已实现下表六类 GET，并挂载到现有 FastAPI。展示 DTO 采用领域模型的白名单投影；前端的 fixture 与真实 API 共用 Zod 校验和页面。

- [x] 依据已有Pydantic模型起草展示DTO，放入 `evoteam/presentation/models.py`，前端对应类型集中保存；不复制修改核心领域模型。
- [x] 准备成功、失败、待采样、缺证据四类fixture，覆盖null指标和重复执行实例；开发样例必须持续标记为fixture。
- [ ] 把消费字段和缺失端口清单交给A，使用下表约定，不要求负责人写接口设计。
- [ ] 从已提交历史JSON选择可展示的Run/Evolution ID，B检查可用字段，A核对来源；缺少完整快照的图留空。

共用展示外层：`schema_version`、`source_kind`、`captured_at`、`code_commit`（未知为null）、`data`、`missing_refs`。来源固定为fixture / recorded_model_run / current_database；来源属于展示元数据，不回写原始SealedRun。

| 已实现的展示 HTTP 接口 | A提供的存储能力 | B的行为要求 |
| --- | --- | --- |
| `GET /v1/runs?strategy_id=&purpose=&limit=&cursor=` | A0 list_runs | data包含items: SealedRun[]、next_cursor，明确用途/范围 |
| `GET /v1/runs/{run_id}` | get_sealed_run + read_snapshot | 返回Task/Strategy/Run/Evaluation；无快照标缺失，不从索引造计划 |
| `GET /v1/runs/{run_id}/events` | events_for_run | sequence有序，caused_by可追踪，node与instance分开 |
| `GET /v1/strategies/{strategy_id}/versions` | A0 list_versions + current | 展示版本及唯一服务指向，不推测状态变化时间 |
| `GET /v1/evolutions?strategy_id=&limit=&cursor=` | A0 list_records | items与next_cursor，稳定分页 |
| `GET /v1/evolutions/{evolution_id}` | get_record / proposal / attribution / validation | 读取已有引用闭包；缺失引用列入missing_refs |

A0约定的列表返回 `(items_tuple, next_cursor)`；缺失单条记录为KeyError。B将存储返回映射为展示DTO及HTTP状态：资源根ID不存在404，非法过滤/分页参数400或框架422，已存在记录的部分证据缺失返回可读data＋missing_refs。模型版本、时间与成本缺失时显示未知。

B不重新计算成功率/Gate/子类收益。已支持 N3 提供的逐题配对数据；旧记录只有聚合指标时只显示聚合。只读浏览、刷新、回放不能调用run/evolve；不做手工晋级按钮。

## 3. B1–B4 执行要求
## B1：前端页面与交互，可从现在开始

**首版已交付，继续维护。** 严格按 [FRONTEND_SPEC](FRONTEND_SPEC.md) 的四类页面、布局、设计变量和交互规则开发。先交付运行详情和 Trace 代表页面供设计验收，再复用组件完成其余页面；使用静态证据包启动，缺接口不阻塞页面开发。

| 页面 | 画面与交互 | 依赖证据 | 验收 |
| --- | --- | --- | --- |
| 运行列表与任务详情 | 策略/用途筛选；状态过滤若仅针对当前页必须标明，点击 Run 查看任务、排期、规则错误与用量 | SealedRun + Snapshot | 成功、失败、超时、空列表均可读；cost 未知显示“未提供” |
| 团队与 Trace | 配置图、实际执行次序、事件列表、点击节点打开输入/输出抽屉 | execution_plan、instances、events | retry 用不同 instance 展示；三角色五次实例不画成五种 Role；多上游来源可追踪 |
| 演进详情 | Trigger → 证据 → 归因 → Proposal Diff → Validation → Gate | 完整演进证据包 | Candidate 与 Current 标清；Reject、待采样、无候选和缺证据都有页面状态 |
| 版本与指标 | 正式版本线、候选比较面板、用量和成功/失败概览 | 策略/治理记录、过滤后的指标 | 候选画在比较区域，不画成 Strategy Family；N3 前不展示不存在的逐题置信或子类结论 |

数据与演进展示均在本轮工作范围。图上区分配置节点、实际实例和业务控制器；颜色不能成为区分状态的唯一方式。先支持桌面演示尺寸与截图，不增加拖拽改策略、手工晋级、账户管理或自动启动模型的按钮。

- [ ] B0 确认最低响应 Schema，准备成功/失败/待采样/缺数据四类 fixture 并标明来源。
- [ ] 在 `frontend/` 建页面和数据读取适配层，以 fixture 接口开发；保持 API 路径和数据绑定集中管理。按 FRONTEND_SPEC 先交运行详情/Trace 的桌面、窄屏及异常态样稿，后续四页复用同一套组件。
- [ ] 测试过滤、详情导航、重复实例、null 指标、断网和缺证据状态。
- [ ] 交付可启动的页面及演示路线截图样张，不把 fixture 截图当真实运行结果。

## B2：只读查询与脱敏导出

**六类 GET 与 Run 导出已交付，Evolution 导出待补。** 维护 `evoteam/api_queries.py`、`evoteam/presentation/`；新建 `tests/test_api_queries.py`、`tests/test_evidence_export.py`。

- [ ] 根据 B0 契约给现有 get/read 接口加查询包装；新列表查询使用分页和稳定排序，不一次加载全部历史。
- [ ] 加入 `tests/test_api_queries.py`：404、空列表、用途隔离、分页、部分证据缺失，以及读取不写数据库的断言。
- [ ] 增加脱敏导出：显式选择 Run / Evolution ID，导出引用闭包；缺少数据库中的 snapshot/trace 时列出 missing_refs。只拥有 SealedRun JSON 不能导出完整执行甘特图。
- [ ] 对输出字段使用白名单；测试不导出密钥、模型服务连接配置或系统绝对路径。
- [ ] 保证刷新/打开页面只使用查询接口；测试过程中记录 Runtime 调用次数为零。

**验收：** 页面与导出读取同一套证据；打开、筛选、回放不会触发模型或演进。GET 端点在本任务实现前不能在其他文档中写成已有能力。

## B3：真实证据联调和截图

**主责：B；A提供可共享证据并排查读模型问题，项目负责人只核对。** 依赖 B1/B2；旧库使用 N1 升级，绝不为演示清空库。

- [ ] 用一份真实记录替换 fixture，逐个核对 ID、策略版本、评价、Token、Gate 理由。
- [ ] 可优先使用已脱敏的历史 JSON 做列表和 Gate 展示；Trace、排期和节点输入输出必须等待对应完整快照。没有的数据留空。
- [ ] 录制“任务结果 → Trace → 演进详情 → Gate → 当前版本”60–90 秒路径，并保留离线证据包作为网络异常备份。
- [ ] 按 [PPT 设计文档](PRESENTATION_PLAN.md) 的 S01–S06 素材清单导出截图，保存版本/来源说明。

**验收：** 现场不要求临时完成多轮付费验证；可以明确标注为历史回放。演示网络失败时仍能展示经过核对的旧证据。

## B4：PPT 和讲稿，与 B1 并行

**主责：B。** 负责人审核业务表述、数字和结论，A 核对实现边界。具体每页文案、布局坐标、状态与图片槽位以 [PRESENTATION_PLAN](PRESENTATION_PLAN.md) 为唯一设计源。

- [ ] 先完成封面、问题、领域对象、架构、两个闭环、候选和 Gate 的可编辑图形；先不填缺失截图。
- [ ] 按来源登记表填历史结果页；保留样本数量、日期、未知指标和缺失证据说明。
- [ ] B3 完成后替换截图占位；N4 有新结果再替换对应数据页，整页更新来源，不混搭历史数字与新版本截图。
- [ ] B整理讲稿初稿并计时预演，负责人审核并彩排；B 导出 `.pptx`、PDF 和离线演示素材。字幕、截图和版本信息一并检查。

**验收：** 每页只有一个明确结论；已有实现、历史实测、机制示例和待实现状态不混淆。没有真实晋级时讲清拒绝路径，不填虚构收益。


## 4. 耦合关系与等待期间的工作

| 依赖 | 谁生产 | B收到什么才进入联调 | 等待时继续做什么 |
| --- | --- | --- | --- |
| 分页/版本查询 | A0 | 可从main读取的端口、签名、错误和排序说明 | fixture适配、页面、PPT文案和原生图 |
| 旧数据库升级 | A的N1 | 升级命令与通过的测试 | 新临时库/脱敏历史JSON联调，不自行清空或迁移旧库 |
| 逐任务验证指标 | A的N3 | 新增字段、兼容说明和测试样例 | 展示已存在聚合指标；逐题页面显示待提供 |
| 真实实验材料 | A的N4 | 可共享记录/ID、原始来源、结论初稿和限制 | 使用标明日期的历史结果；不虚构新实验数字 |

B负责完整查询包装和前端适配；A补核心端口；发现不兼容时双方各自修改所维护的代码，负责人只审核。

无需等待N4才交付PPT。先交“结构/架构页完整＋截图/新结果空槽”的可编辑稿；已有历史Reject记录可以合法展示，但必须使用历史标签。等真实证据就绪再交成稿。没有证据不能用动画把示意伪装成实测。

## 5. PPT交付与负责人验收

- B写每页讲稿初稿、整理素材、录制演示，负责人检查叙事与结论并主讲，不要求负责人从空白制作。
- 第一交付：按PRESENTATION_PLAN完成14页主稿＋4页备份的可编辑布局、文字和图；缺截图保持编号槽位。
- 第二交付：真实可用截图、来源清单、60–90秒演示或静态备份、可编辑PPT与PDF。时间/官方模板调整由负责人确认，B执行修改。
- 若两线进度不同，先交已有证据的阶段演示，不宣称完整项目验收。

## 6. 验证与停止边界

- [ ] 读取/过滤/空数据/断网/缺引用/null指标/重复实例测试通过；读取不得有数据库写入或模型调用。
- [ ] B0–B4交付完整，A尚未交付部分精确列为依赖，不替A标记完成。
- [ ] 截图中的每个数字有来源，PPT字体/溢出/图形位置经过逐页检查，PDF和离线演示可打开。
- [ ] 自己的API router已接入且原POST契约测试仍通过，不留下“负责人再写一行才能跑”的事项。

执行Python检查：`uv sync`、`uv run pytest`、`uv run ruff check .`、`uv run ruff format --check .`、`uv run pyright`；前端开工后在其README记录实际安装/构建/测试命令并运行。不要把尚未建好的前端命令宣称通过。

前端的布局、每区内容、动画、按钮行为及异常状态只维护在 FRONTEND_SPEC，本任务书维护交付进度，不另起平行设计稿。

每次按AGENTS汇报，另列“依赖A的交付”“当前采用的数据来源”“尚未填充的素材槽位”。只交付本任务，其他功能不自动开工。

团队成果统一纳入main后再通知组员读取；任务分支仅供开发隔离，不能作为长期成果入口。PPT完整内容仍只维护PRESENTATION_PLAN，不新建互相冲突的设计版本。
