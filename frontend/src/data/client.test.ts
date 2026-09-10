import { expect, it, vi } from "vitest";
import { readEvidence } from "./client";
import { runSchema } from "./schema";
it("does not fall back to fixture when the API is offline", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  await expect(
    readEvidence(
      "/runs/missing",
      runSchema,
      new AbortController().signal,
      "api",
    ),
  ).rejects.toThrow();
  vi.unstubAllGlobals();
});
it("rejects invalid evidence DTOs", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        schema_version: "1",
        source_kind: "current_database",
        data: { run_id: 42 },
      }),
    }),
  );
  await expect(
    readEvidence("/runs/bad", runSchema, new AbortController().signal, "api"),
  ).rejects.toThrow();
  vi.unstubAllGlobals();
});
