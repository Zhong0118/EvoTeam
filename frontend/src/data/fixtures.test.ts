import { describe, expect, it } from "vitest";
import { fixtureData } from "../fixtures/evidence";
import {
  evolutionDetailSchema,
  eventsSchema,
  pageSchema,
  runSchema,
  versionsSchema,
} from "./schema";
describe("sample evidence follows the same DTOs as the API", () => {
  it("covers success, failure, unknown metrics and repeated instances", () => {
    const page = pageSchema(runSchema).parse(
      fixtureData("/runs?strategy_id=demo-project-planning"),
    );
    expect(page.items.map((r) => r.evaluation.metrics.success)).toEqual([
      true,
      false,
      true,
      null,
    ]);
    expect(
      page.items[1].instances?.filter((i) => i.node_id === "executor"),
    ).toHaveLength(2);
    expect(page.items[3].evaluation.metrics.tokens).toBeNull();
    eventsSchema.parse(fixtureData("/runs/fixture-run-2/events"));
  });
  it("keeps insufficient sampling and missing evidence distinct", () => {
    const detail = evolutionDetailSchema.parse(
      fixtureData("/evolutions/fixture-evolution-1"),
    );
    expect(detail.record.promoted).toBeNull();
    expect(detail.record.gate_results[0].decision).toBe("continue_sampling");
    expect(
      evolutionDetailSchema.parse(
        fixtureData("/evolutions/fixture-evolution-2"),
      ).validations,
    ).toEqual([]);
    versionsSchema.parse(
      fixtureData("/strategies/demo-project-planning/versions"),
    );
  });
});
