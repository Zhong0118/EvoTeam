# EvoTeam

> **Building Multi-Agent Teams That Learn, Adapt, and Evolve.**

EvoTeam 是一个基于 **openJiuwen Core** 构建的自演进多智能体协作系统。

当前项目目标不是尽快堆出一个 Demo，而是先回答清楚：

1. 为什么复杂任务需要多智能体协作？
2. Agent Team 应该如何动态形成与调度？
3. 系统如何判断一次协作是成功还是失败？
4. 系统如何从历史任务中学习并改变下一次协作策略？
5. 如何证明“演进”真实有效，而不是简单 Retry 或改 Prompt？

---

## 当前阶段

项目目前处于：

```text
产品定义 / 架构设计 / 实验设计
```

而不是大规模功能开发阶段。

近期优先级：

```text
明确产品定位
    ↓
明确核心创新
    ↓
明确架构边界
    ↓
明确实验方法
    ↓
形成汇报材料
    ↓
再进入 MVP 开发
```

---

## 当前技术基线

- Python 3.12
- uv
- openJiuwen Core
- FastAPI（后端候选）
- React + TypeScript（前端候选）
- SQLite → PostgreSQL（按阶段演进）

当前原则：

> openJiuwen 负责 Agent 的基础运行能力，EvoTeam 负责 Team 的组织、评价与演进。

---

## 文档导航

| 文档 | 作用 |
| --- | --- |
| `DEVELOPMENT.md` | 本地环境、uv、Git 协作 |
| `AGENTS.md` | Coding Agent 开发规则 |
| `docs/PROJECT.md` | 赛题与项目定义 |
| `docs/PRODUCT_VISION.md` | 产品愿景、核心假设与待决策问题 |
| `docs/ARCHITECTURE.md` | 当前系统架构草案 |
| `docs/ROADMAP.md` | 从产品设计到比赛版本的阶段计划 |
| `docs/EXPERIMENTS.md` | 自演进实验与评价设计 |
| `docs/DECISIONS.md` | 关键架构/产品决策记录 |
| `docs/PRESENTATION_PLAN.md` | 近期汇报 PPT 结构与素材清单 |

---

## 项目状态说明

当前文档中会使用以下标签：

- **[确定]**：当前团队已经接受，可直接作为开发约束。
- **[假设]**：目前认为合理，但需要实验或讨论验证。
- **[待定]**：尚未做决定，不应由 Coding Agent 擅自选择。

---

## 当前最重要的原则

> Make it observable before making it intelligent.  
> Make it evaluable before making it evolve.  
> Make evolution reversible before making it automatic.

对应中文：

> 先让系统可观察，再让系统更智能。  
> 先让结果可评价，再让系统自演进。  
> 先让演进可回滚，再让演进自动化。
