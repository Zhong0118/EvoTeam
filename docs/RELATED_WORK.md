# EvoTeam 相关工作参考

本文件保留原有讨论中的文献入口，供后续技术调研与引用核验使用。当前实现规范以 PROJECT、ARCHITECTURE、DECISIONS 为准；文献中出现的 Family、开放搜索或自动系统生成不会因此进入当前范围。

## 项目比较维度

后续阅读与汇报围绕以下问题整理证据：

- 改变发生在同一任务内，还是能持久影响未来任务？
- 被改变的是 Prompt、Skill、AgentConfig、通信拓扑还是整体 Strategy？
- 是否以跨 Run 证据触发，是否识别错误来源与控制失效？
- 是否通过独立数据验证，是否记录成本、负迁移与拒绝候选？
- 是否存在版本治理、稳定停止、重新触发和退化回滚？

EvoTeam 当前设计聚焦固定 Role Pool 下、单条 Strategy 版本链的受约束组织演进。三项核心主张是 Strategy as Evolvable Organization、Evidence-driven Bounded Organization Mutation、Evolution Governance；这些主张的效果由本项目实验验证，不据此宣称其他平台无法实现类似能力。

## 既有参考入口

以下链接从原有文档保留，本轮为文档一致性整理，未重新核验论文元数据、全文结论或框架最新能力。正式引用前核对标题、作者、版本和支持论点的原文，不能直接复用旧稿中的比较断言。

| 参考名称 | 来源 |
| --- | --- |
| Reflexion | [原始参考入口 1](https://arxiv.org/abs/2303.11366) |
| Voyager | [原始参考入口 1](https://arxiv.org/abs/2305.16291) |
| DyLAN | [原始参考入口 1](https://arxiv.org/abs/2310.02170) |
| GPTSwarm | [原始参考入口 1](https://arxiv.org/abs/2402.16823) |
| AgentPrune | [原始参考入口 1](https://arxiv.org/abs/2410.02506) |
| Adaptive Graph Pruning | [原始参考入口 1](https://arxiv.org/abs/2506.02951) |
| EvoAgent | [原始参考入口 1](https://arxiv.org/abs/2406.14228) |
| EvoMAS | [原始参考入口 1](https://arxiv.org/abs/2602.06511) |
| ADAS | [原始参考入口 1](https://arxiv.org/abs/2408.08435) |
| AFlow | [原始参考入口 1](https://arxiv.org/abs/2410.10762) |
| Meta-Team | [原始参考入口](https://arxiv.org/abs/2605.29790) |
| JiuwenSwarm | [官方仓库](https://github.com/openJiuwen-ai/jiuwenswarm) |
| A Survey of Self-Evolving Agents | [原始参考入口 1](https://arxiv.org/abs/2507.21046) |
| A Comprehensive Survey of Self-Evolving AI Agents | [原始参考入口 1](https://arxiv.org/abs/2508.07407) |
| RSI 与自我改进边界 | [原始参考入口 1](https://arxiv.org/abs/1502.06512)、[原始参考入口 2](https://arxiv.org/abs/2601.05280) |

项目计划书还列出 ExpeL、Promptbreeder 与 Why Do Multi-Agent LLM Systems Fail? 等阅读方向，以及 Bedrock、AutoGen、LangGraph、GitLab Duo 的框架比较。对应原文与版本应在正式研究任务中补齐，不根据简称猜测链接。

## 与项目的衔接

运行框架的 API 与能力以实际接入的锁定版本验证。openJiuwen 在本项目中承担 Runtime 角色，EvoTeam 自己维护领域模型、跨任务证据、Mutation、Validation 与生命周期；这是一项项目内边界划分，不是对整个 openJiuwen 生态能力的排他判断。

结构搜索与团队生成相关工作用于审视 Mutation 空间，剪枝相关工作用于设计贡献和成本实验，经验及失败分析用于设计归因基准。当前不直接复制遗传搜索、自由代码生成或 Family 体系。

正式汇报只使用已核验的原文与有实验支持的差异；详细实验口径见 [EXPERIMENTS.md](EXPERIMENTS.md)。
