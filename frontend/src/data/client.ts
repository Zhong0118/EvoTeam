import { useEffect, useState } from "react";
import { z } from "zod";
import { envelopeSchema, type Envelope } from "./schema";
export const source =
  import.meta.env.VITE_DATA_SOURCE === "fixture" ? "fixture" : "api";
export const defaultStrategy = import.meta.env.VITE_STRATEGY_ID || "";
export async function readEvidence<T>(
  path: string,
  schema: z.ZodType<T>,
  signal: AbortSignal,
  mode: string = source,
): Promise<Envelope<T>> {
  let body: unknown;
  if (mode === "fixture") {
    const { fixtureData } = await import("../fixtures/evidence");
    body = {
      schema_version: "1",
      source_kind: "fixture",
      captured_at: "2026-09-09T08:30:00Z",
      code_commit: null,
      missing_refs: [],
      data: fixtureData(path),
    };
  } else {
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE || ""}/v1${path}`,
      { signal, method: "GET", headers: { Accept: "application/json" } },
    );
    if (!response.ok)
      throw new Error(
        response.status === 404
          ? "404：该记录不存在"
          : `查询失败（${response.status}）。请检查 API 服务与数据库配置。`,
      );
    body = await response.json();
  }
  const parsed = envelopeSchema(schema).safeParse(body);
  if (!parsed.success)
    throw new Error("数据格式与展示协议不一致，请更新服务与前端版本。");
  return parsed.data as Envelope<T>;
}
export function useEvidence<T>(path: string | null, schema: z.ZodType<T>) {
  const [state, setState] = useState<{
    key: string | null;
    value?: Envelope<T>;
    error?: string;
  }>({ key: null });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    readEvidence(path, schema, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setState({ key: path, value });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({
            key: path,
            error: error instanceof Error ? error.message : "查询失败",
          });
      });
    return () => controller.abort();
  }, [path, schema, revision]);
  const current: typeof state = state.key === path ? state : { key: path };
  return {
    value: current.value,
    error: current.error,
    loading: !!path && !current.value && !current.error,
    refresh: () => {
      setState({ key: null });
      setRevision((n) => n + 1);
    },
  };
}
