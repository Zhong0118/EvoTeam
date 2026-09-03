# EvoTeam Decisions V1

以下产品级决策视为当前 V1 已接受。

| ID | 决策 | 状态 |
| --- | --- | --- |
| D-001 | Python 3.12 | Accepted |
| D-002 | uv 管理项目环境 | Accepted |
| D-003 | openJiuwen Core 作为 Runtime 基础 | Accepted |
| D-004 | 初始化阶段只维护 main | Accepted |
| D-005 | 先产品/实验，后大规模编码 | Accepted |
| D-006 | Strategy 是核心演进单元 | Accepted |
| D-007 | Task-Driven Team + Role-Based Agents | Accepted |
| D-008 | V1 固定 Role Pool，动态 Skill/Tool/Strategy | Accepted |
| D-009 | Strategy Family + Variant | Accepted |
| D-010 | Base + Variant Delta | Accepted |
| D-011 | AD_HOC → Candidate → Persistent Variant | Accepted |
| D-012 | 支持 Specialization / Generalization | Accepted |
| D-013 | 支持 Freeze / Unfreeze | Accepted |
| D-014 | Event / Run / Window 三层经验粒度 | Accepted |
| D-015 | Memory 与 Evolution 分离 | Accepted |
| D-016 | Rule/统计信号触发 Evolution | Accepted |
| D-017 | Failure Attribution 为核心模块 | Accepted |
| D-018 | Rule + Trace + LLM Attribution | Accepted |
| D-019 | 多因 Attribution | Accepted |
| D-020 | Counterfactual Replay | Deferred V1.5 |
| D-021 | Typed Mutation Operator | Accepted |
| D-022 | 每次 Evolution 2~3 Candidates | Accepted |
| D-023 | Minimal Mutation | Accepted |
| D-024 | Static → Smoke → Mini → Full Validation | Accepted |
| D-025 | Held-out Validation Gate 决定换代 | Accepted |
| D-026 | Promotion 同时考虑质量、效率、复杂度 | Accepted |
| D-027 | Growth 与 Pruning 同等重要 | Accepted |
| D-028 | Team = constrained typed graph | Accepted |
| D-029 | V1 不宣称 RSI | Accepted |
| D-030 | Evolution Governance 作为产品差异化概念 | Accepted |

## 仍由实验决定的参数

以下不需要靠产品讨论硬拍板：

- Evolution Window 大小
- Failure Trigger 阈值
- Attribution Confidence 阈值
- Candidate 数量最终为 2 还是 3
- Smoke / Mini / Full Validation 数据量
- Quality Improvement 阈值
- Cost / Latency Guardrail
- Freeze 判定阈值
