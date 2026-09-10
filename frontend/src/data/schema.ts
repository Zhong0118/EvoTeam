import { z } from "zod";
export const refSchema = z.object({
  strategy_id: z.string(),
  version: z.number(),
});
const asset = z.object({ id: z.string(), version: z.string() });
const metrics = z.object({
  quality: z.number().nullable(),
  success: z.boolean().nullable(),
  hard_constraint_errors: z.number().nullable(),
  tokens: z.number().nullable(),
  cost: z.number().nullable(),
  latency_seconds: z.number().nullable(),
  agent_count: z.number().nullable(),
  tool_calls: z.number().nullable(),
  retry_count: z.number().nullable(),
});
export const nodeSchema = z.object({
  node_id: z.string(),
  config_id: z.string(),
  role: z.string(),
  prompt_ref: asset,
  model_ref: asset,
  skill_refs: z.array(asset),
  tool_policy: z.object({
    allowed_tools: z.array(asset),
    required_tools: z.array(asset),
  }),
});
const edge = z.object({
  source: z.string(),
  target: z.string(),
  condition_ref: asset.nullable(),
});
const evaluation = z.object({
  metrics,
  evaluator_ref: asset,
  issues: z.array(
    z.object({
      code: z.string(),
      message: z.string(),
      severity: z.string(),
      evidence_refs: z.array(z.string()),
      node_id: z.string().nullable(),
    }),
  ),
  missing_metrics: z.array(z.string()),
});
export const runSchema = z.object({
  run_id: z.string(),
  task_id: z.string(),
  task_scope: z.string(),
  strategy: refSchema,
  purpose: z.enum(["online", "validation", "final_test", "diagnostic"]),
  status: z.string(),
  sealed_at: z.string(),
  evaluation,
  task: z
    .object({
      task_id: z.string(),
      instruction: z.string(),
      inputs: z
        .object({
          goal: z.string(),
          deadline_hour: z.number(),
          budget_minor: z.number(),
          currency: z.string(),
          work_items: z.array(
            z.object({
              work_id: z.string(),
              description: z.string(),
              dependencies: z.array(z.string()),
            }),
          ),
          people: z.array(
            z.object({ person_id: z.string(), skills: z.array(z.string()) }),
          ),
        })
        .nullable(),
    })
    .nullable()
    .optional(),
  plan: z
    .object({
      schedule: z.array(
        z.object({
          work_id: z.string(),
          person_id: z.string(),
          start_hour: z.number(),
          end_hour: z.number(),
        }),
      ),
      risks: z.array(z.string()),
      adjustments: z.array(z.string()),
      validation_notes: z.array(z.string()),
    })
    .nullable()
    .optional(),
  nodes: z.array(nodeSchema).optional(),
  edges: z.array(edge).optional(),
  instances: z
    .array(
      z.object({
        instance_id: z.string(),
        node_id: z.string(),
        state: z.string(),
        messages: z.array(
          z.object({
            message_id: z.string(),
            sender_node_id: z.string().nullable(),
            recipient_node_id: z.string(),
            source_event_ids: z.array(z.string()),
          }),
        ),
        output: z.unknown().nullable(),
      }),
    )
    .optional(),
  termination_reason: z.string().nullable().optional(),
});
export const eventSchema = z.object({
  event_id: z.string(),
  event_type: z.string(),
  timestamp: z.string(),
  sequence: z.number(),
  run_id: z.string().nullable(),
  node_id: z.string().nullable(),
  instance_id: z.string().nullable(),
  caused_by: z.array(z.string()),
});
export const strategySchema = z.object({
  metadata: z.object({
    ref: refSchema,
    parent: refSchema.nullable(),
    generation: z.number(),
    status: z.string(),
  }),
  definition: z.object({
    agents: z.array(nodeSchema),
    edges: z.array(edge),
    orchestration: z.record(z.string(), z.unknown()).optional(),
  }),
});
const gate = z.object({
  validation_id: z.string(),
  decision: z.string(),
  policy_ref: asset,
  reasons: z.array(z.string()),
  improvement_attribution_ref: z.string(),
});
export const evolutionSchema = z.object({
  evolution_id: z.string(),
  trigger: z.object({
    trigger_id: z.string(),
    strategy: refSchema,
    trigger_type: z.string(),
    reason: z.string(),
    evidence_run_ids: z.array(z.string()),
    policy_ref: asset,
  }),
  candidates: z.array(refSchema),
  gate_results: z.array(gate),
  promoted: refSchema.nullable(),
  rollback_target: refSchema.nullable(),
  termination_reason: z.string().nullable(),
});
const summary = z.object({
  success_count: z.number(),
  total_count: z.number(),
  independent_task_count: z.number(),
});
export const validationSchema = z.object({
  validation_id: z.string(),
  current: refSchema,
  candidate: refSchema,
  plan: z.object({
    dataset_ref: asset,
    evaluator_ref: asset,
    repeats: z.number(),
  }),
  current_metrics: metrics,
  candidate_metrics: metrics,
  current_summary: summary.nullable(),
  candidate_summary: summary.nullable(),
  limitations: z.array(z.string()),
  pairs: z.array(
    z.object({
      task_id: z.string(),
      subclass: z.string(),
      repeat_index: z.number(),
      current_run_id: z.string(),
      candidate_run_id: z.string(),
      current_metrics: metrics,
      candidate_metrics: metrics,
    }),
  ),
});
export const evolutionDetailSchema = z.object({
  record: evolutionSchema,
  attributions: z.array(
    z.object({
      report_id: z.string(),
      task_scope: z.string(),
      needs_more_evidence: z.boolean(),
      claims: z.array(
        z.object({
          kind: z.string(),
          target: z.string(),
          explanation: z.string(),
          confidence: z.number(),
          evidence_refs: z.array(z.string()),
        }),
      ),
    }),
  ),
  proposals: z.array(
    z.object({
      proposal_id: z.string(),
      operation: z.string(),
      target: z.string(),
      rationale: z.string(),
      attribution_ref: z.string(),
    }),
  ),
  validations: z.array(validationSchema),
  strategies: z.array(strategySchema),
});
export const pageSchema = <T extends z.ZodType>(schema: T) =>
  z.object({ items: z.array(schema), next_cursor: z.string().nullable() });
export const eventsSchema = z.object({ items: z.array(eventSchema) });
export const versionsSchema = z.object({
  items: z.array(strategySchema),
  current: refSchema.nullable(),
});
export type Run = z.infer<typeof runSchema>;
export type TraceEvent = z.infer<typeof eventSchema>;
export type Evolution = z.infer<typeof evolutionSchema>;
export type Validation = z.infer<typeof validationSchema>;
export type Strategy = z.infer<typeof strategySchema>;
export type Envelope<T> = {
  schema_version: "1";
  source_kind: "fixture" | "recorded_model_run" | "current_database";
  captured_at: string;
  code_commit: string | null;
  missing_refs: string[];
  data: T;
};
export function envelopeSchema<T extends z.ZodType>(data: T) {
  return z.object({
    schema_version: z.literal("1"),
    source_kind: z.enum(["fixture", "recorded_model_run", "current_database"]),
    captured_at: z.string(),
    code_commit: z.string().nullable(),
    missing_refs: z.array(z.string()),
    data,
  });
}
