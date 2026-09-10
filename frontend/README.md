# EvoTeam 证据工作台

React + TypeScript + Vite、Tailwind v4、基于 Radix 的 shadcn/ui 源码组件模式、React Flow、Recharts。视觉参考 [AIHOT](https://aihot.news/) 的窄导航、浅灰背景和内容层级；页面含义以 EvoTeam 的现行领域规范为准。Node **24.19.0** / npm **11.17.0** 已验证，依赖版本以 package-lock.json 为准。

## 启动开发样例

在本目录执行：

```bash
npm ci
VITE_DATA_SOURCE=fixture VITE_STRATEGY_ID=demo-project-planning npm run dev
```

打开 http://127.0.0.1:5173 。顶部始终标明“开发样例 · 非实测”。样例覆盖成功、评价失败、超时缺快照、重复实例、待采样、缺归因/验证。`screenshots/` 是这些样例的视觉验收图，不能作为真实实验结果放入 PPT。

## 连接数据库

默认数据源为 API，不会因网络错误自动切换样例。在仓库根目录通过后端环境变量指定**已初始化的** SQLite 数据库，运行：

```bash
EVOTEAM_DATABASE_URL=sqlite:////absolute/path/evidence.sqlite3 uv run python -m evoteam serve
```

另开终端，在 frontend 目录执行：

```bash
VITE_DATA_SOURCE=api VITE_STRATEGY_ID=实际的策略ID npm run dev
```

也可复制 `.env.example` 到 `.env.local` 保存公开配置。Vite 将 `/v1` 代理到 `http://127.0.0.1:8000`；后端换端口时设置 `EVOTEAM_PROXY_TARGET`。前端变量不得包含模型密钥。切换来源需重启 Vite，浏览器刷新后清除旧来源的状态。

没有数据库时，GET 返回 503，不自动创建、初始化或迁移。可先在仓库根目录执行 `uv run python -m evoteam demo --database /tmp/evoteam-ui-demo.sqlite3` 创建**全新**、无模型的演示库，策略 ID 是 `demo-project-planning`。它仍是机制演示，不是实测结果。现有实验库必须使用自己的策略 ID，不能凭列表推测全量目录。

生产构建执行 `npm run build`，输出 `dist/`；发布环境需要同源 `/v1` 反向代理和 SPA 路由回退。当前交付为本地工作台，不包含公网部署与鉴权。

## 已实现页面与接口

- `/runs`：按策略和用途筛选、稳定 cursor 分页、复制 ID、刷新。
- `/runs/:runId`：原始任务、结构化排期、评价问题、用量、脱敏 Run 下载。
- `/runs/:runId/trace`：配置拓扑、实际实例、事件因果引用、选择抽屉、600ms 手动历史回放；手机纵向拓扑。
- `/evolutions` 与 `/evolutions/:evolutionId`：触发、归因陈述、候选配置差异、逐题验证、Gate 已存理由。
- `/strategies/:strategyId`：正式版本与隔离候选分区、服务引用、最多两个配置比较。全局指标未提供时明确留空。

`evoteam/api_queries.py` 提供任务书约定的六类 GET 和 `GET /v1/runs/{run_id}/export`。采用 SQLite `mode=ro`，仅使用 A 已提供的读端口。HTTP 展示 DTO 是领域对象的白名单投影，外层 schema_version=1；前端 `data/schema.ts` 通过 Zod 校验。导入、打开页面、刷新、回放均不执行 Run/Evolve。

原始运行 context、SDK 日志和输入消息 payload 不向页面发送。节点输入通过原始任务及上游消息来源查看；输出只展示已支持的规划 Schema。金额缺币种、未知 Token、缺快照、缺引用不补造值。Run 导出保存该 Run 的投影与事件；Evolution 引用闭包下载、历史实测包导入尚未交付。

## 检查

```bash
npm run typecheck
npm run build
npm run lint
npm test
npx playwright install chromium
npm run test:e2e
```

本机已有 Chrome 时可使用 `PLAYWRIGHT_CHANNEL=chrome npm run test:e2e`。E2E 自动启动两个 Vite 服务及独立临时 FastAPI/SQLite 演示服务，端口 5174、5175、8765 必须空闲；不读取个人 .env，不调用模型，不修改项目数据库。浏览器测试包含 API 只读网络断言、真实 HTTP 数据绑定、离线、过滤、重复实例、抽屉、窄屏、404 与截图。截图输出到 `screenshots/`。

## 代码入口

`app/layout.tsx` 管导航与来源说明；`pages/` 管四类页面；`components/evidence/` 管共用证据表达和配置差异；`data/` 管校验与读取；`fixtures/` 管显式样例；`styles/theme.css` 管统一视觉与响应式。修改产品规则前阅读 `../docs/FRONTEND_SPEC.md`。
