# EvoTeam Architecture V1

> 与 Product Spec V1 对齐。

## 1. 总体架构

```text
┌────────────────────────────────────────────────────┐
│                 Evolution Console                  │
│ Task / Strategy / Team Graph / Trace / Evaluation │
│ Evolution Diff / Validation / Generation History  │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│                   EvoTeam Core                     │
│                                                    │
│ Task Analyzer ───────→ Strategy Router             │
│ Strategy Library ────→ Team Orchestrator           │
│                           │                        │
│                           ▼                        │
│                       Run / Trace                  │
│                           │                        │
│                           ▼                        │
│                        Evaluator                   │
│                           │                        │
│                           ▼                        │
│                    Experience Store                │
│                           │                        │
│                           ▼                        │
│                    Signal Detector                 │
│                           │                        │
│                           ▼                        │
│                  Failure Attribution               │
│                           │                        │
│                           ▼                        │
│                    Mutation Planner                │
│                           │                        │
│                           ▼                        │
│                    Candidate Pool                  │
│                           │                        │
│                           ▼                        │
│                     Validation Gate                │
│                      ↙           ↘                 │
│                 Promote          Reject            │
│                    │                               │
│                    ▼                               │
│               Strategy Registry                    │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│              Runtime Abstraction Layer             │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│                OpenJiuwen Adapter                  │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│               openJiuwen agent-core               │
│ Agent / Model / Tool / Workflow / Runtime         │
└────────────────────────────────────────────────────┘
```

## 2. 执行链

```text
Task
 ↓
Task Analyzer
 ↓
Task Signature
 ↓
Strategy Router
 ↓
Exact / Similar Variant?
 ├─ Yes → Load
 └─ No  → Parent + Ephemeral Delta
 ↓
Instantiate Team
 ↓
Team Orchestrator
 ↓
Run + Trace
 ↓
Evaluator
 ↓
Seal Run
```

## 3. 演进链

```text
Sealed Runs
 ↓
Evolution Window
 ↓
Signal Detector
 ↓
Failure Pattern?
 ├─ No → Continue
 └─ Yes
      ↓
Failure Attribution
      ↓
Mutation Planner
      ↓
Candidate A / B / C
      ↓
Static Validation
      ↓
Smoke Test
      ↓
Mini Validation
      ↓
Full Validation
      ↓
Promote / Reject
```

## 4. Strategy Library

```text
StrategyLibrary
│
├── Report
│   ├── Base
│   ├── General
│   ├── News
│   └── Academic
│
├── DataAnalysis
│   ├── Base
│   ├── Tabular
│   └── Statistical
│
└── Planning
    ├── Base
    ├── Project
    └── ResourceConstraint
```

## 5. Team Graph

Team 是 Typed Graph：

```text
Node = Role Instance
Edge = Communication / Dependency
```

示例：

```text
                  ┌→ Researcher ─┐
Planner ──────────┤              ├→ Writer → Verifier
                  └→ Analyst ────┘
```

Edge 可携带：

- type
- condition
- priority
- data schema

## 6. Attribution Pipeline

```text
Failure
 ↓
Deterministic Check
 ↓
Trace Provenance
 ↓
Relevant Trace Slice
 ↓
LLM Attribution
 ↓
Attribution Result
```

## 7. Candidate Pipeline

```text
Attribution
 ↓
Mutation Scope
 ↓
2~3 Typed Candidates
 ↓
Minimal Mutation
 ↓
Validation Funnel
```

## 8. Experience

```text
Raw Trace
 ↓
Run Summary
 ↓
Structured Experience
 ↓
Evolution Window
 ↓
Failure Pattern
```

## 9. Runtime Boundary

原则：

```text
EvoTeam Core
    ↓ Protocol
Runtime Adapter
    ↓
openJiuwen Core
```

只有 openJiuwen Adapter 直接依赖 openJiuwen API。

## 10. 前端核心页面

- Task Workspace
- Strategy Library
- Team Graph
- Execution Timeline
- Evaluation Dashboard
- Evolution Center
- Generation History

前端重点：

> **Observable Organization Evolution**

而不是 Chat UI。
