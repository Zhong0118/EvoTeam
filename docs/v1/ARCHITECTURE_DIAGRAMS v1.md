# EvoTeam Architecture Diagrams V1

> 这些是 PPT 制图蓝本。正式 PPT 时应做成矢量图，不建议直接截图 Markdown。

## 图 1：产品总架构

```text
┌──────────────────────────────────────────────┐
│               Evolution Console              │
│ Task │ Strategy │ Team Graph │ Evaluation   │
│ Trace │ Evolution Diff │ Generation History │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│                 EvoTeam Core                 │
│ Task Analyzer      Strategy Library          │
│ Strategy Router    Team Orchestrator         │
│ Evaluator          Experience Store          │
│ Attribution        Mutation Planner          │
│ Validation Gate    Strategy Registry         │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│          Runtime Abstraction / Adapter       │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│              openJiuwen Core                 │
│ Agent │ Model │ Tool │ Workflow │ Runtime   │
└──────────────────────────────────────────────┘
```

## 图 2：完整自演进闭环

```text
Task
 ↓
Strategy
 ↓
Team
 ↓
Run
 ↓
Evaluation
 ↓
Experience
 ↓
Attribution
 ↓
Mutation
 ↓
Validation
 ├→ Promote → Next Generation
 └→ Reject
```

旁边放三句话：

```text
任务决定初始组织
证据决定问题归因
验证决定组织是否换代
```

## 图 3：Strategy Family

```text
                  BaseReportStrategy
                  /       |        \
                 ↓        ↓         ↓
             General     News     Academic
                         │          │
                         │          ├─ paper-search
                         │          ├─ citation-check
                         │          └─ academic-writing
                         │
                         ├─ web-search
                         ├─ freshness-check
                         └─ timeline-check
```

标注：

```text
Parent → Child = Specialization
Child → Parent = Generalization
```

## 图 4：Experience 三层

```text
Trace Events
   ↓
Sealed Run
   ↓
Evolution Window
   ↓
Evolution Trigger
```

标签：

```text
Event = Observe
Run = Learn
Window = Evolve
```

## 图 5：Failure Attribution

```text
                 Failure Detected
                       │
         ┌─────────────┼─────────────┐
         ↓             ↓             ↓
 Deterministic       Trace       LLM Attribution
   Evidence        Provenance
         │             │             │
         └─────────────┼─────────────┘
                       ↓
              Attribution Result
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
      Agent           Tool         Topology
                       │
                       ↓
                Mutation Scope
```

## 图 6：Candidate Competition

```text
               Failure Attribution
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
 Candidate A      Candidate B      Candidate C
 Prompt Update     Tool Policy     Add Verifier
        │              │              │
        └──────────────┼──────────────┘
                       ↓
                Validation Funnel
                       ↓
                 Best Candidate
```

## 图 7：Validation Gate

```text
Current Strategy ───────────┐
                            │
                            ▼
                      Validation Set
                            ▲
                            │
Candidate Strategy ─────────┘
                            │
                            ▼
                Quality / Cost / Latency
                    / Complexity
                            │
                  ┌─────────┴─────────┐
                  ↓                   ↓
               Promote             Reject
```

大字：

> **Same exam, better team wins.**

## 图 8：Growth + Pruning

```text
Before:
Planner → Analyst → Critic → Verifier

Evolution Candidates:
A: + Numeric Verifier
B: - Critic
C: Verifier → Conditional
```

结论：

> **Evolution != More Agents**  
> **Evolution = Better Organization**

## 图 9：Task-Driven Team Formation

```text
                  Task
                   │
                   ↓
             Task Analyzer
                   │
                   ↓
             Task Signature
                   │
       ┌───────────┼───────────┐
       ↓           ↓           ↓
     Report       Data       Planning
       │           │           │
       ↓           ↓           ↓
    Strategy    Strategy    Strategy
       │           │           │
       ↓           ↓           ↓
      Team        Team        Team
```

标注：

> **Task Family != Agent Type**

## 图 10：EvoTeam / openJiuwen 边界

```text
                 EvoTeam
┌────────────────────────────────────────────┐
│ Team Formation                             │
│ Strategy Library                           │
│ Evaluation                                 │
│ Experience                                 │
│ Attribution                                │
│ Evolution                                  │
│ Validation / Promotion / Rollback          │
└─────────────────────┬──────────────────────┘
                      │ Adapter
┌─────────────────────▼──────────────────────┐
│             openJiuwen Core                │
│ Agent / Model / Tool / Workflow / Runtime │
└────────────────────────────────────────────┘
```

这张图用于答辩时说明：

> 哪些能力是 openJiuwen 提供的，哪些是 EvoTeam 自己设计的。
