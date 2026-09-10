import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  Check,
  Copy,
  Database,
  Info,
  RefreshCw,
  ShieldCheck,
  AlertCircle,
  ArrowUpRight,
} from "lucide-react";
import { Button } from "../ui/button";
import type { Envelope } from "../../data/schema";
export const labels: Record<string, string> = {
  online: "线上任务",
  validation: "隔离验证",
  final_test: "最终测试",
  diagnostic: "诊断",
  completed: "运行完成",
  failed: "运行失败",
  timed_out: "已超时",
  cancelled: "已取消",
  current: "Current · 当前服务",
  candidate: "Candidate · 隔离候选",
  rejected: "候选被拒绝",
  stable: "STABLE",
  retired: "已退役",
  draft: "草稿",
  validating: "验证中",
  rolled_back: "已回滚",
  pass: "Gate PASS",
  fail: "Gate 未通过",
  continue_sampling: "待补充样本",
  narrow_scope: "需收窄范围",
  repeated_failure: "重复失败",
  update_prompt: "更新 Prompt",
  add_agent_config: "新增配置",
};
export const human = (v: string) => labels[v] || v;
export const number = (v: number | null | undefined, unit = "") =>
  v == null
    ? "未提供"
    : `${new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(v)}${unit}`;
export const time = (v: string) =>
  new Date(v).toLocaleString("zh-CN", { hour12: false });
export function Badge({
  value,
  children,
}: {
  value?: string;
  children?: ReactNode;
}) {
  return (
    <span className={`badge badge-${value || "neutral"}`}>
      {children || human(value || "")}
    </span>
  );
}
export function CopyId({ id }: { id: string }) {
  const [message, setMessage] = useState("");
  return (
    <span className="copy-id">
      <code title={id}>{id}</code>
      <Button
        size="icon"
        variant="ghost"
        aria-label={`复制 ${id}`}
        onClick={() => {
          navigator.clipboard
            .writeText(id)
            .then(() => setMessage("已复制"))
            .catch(() => setMessage("复制失败，请选择 ID 文本复制"));
        }}
      >
        {message === "已复制" ? <Check size={14} /> : <Copy size={14} />}
      </Button>
      <span className="sr-only" role="status">
        {message}
      </span>
    </span>
  );
}
export function Panel({
  title,
  aside,
  children,
  className = "",
}: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="section-heading">
        <h2>{title}</h2>
        {aside}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}
export function Empty({
  title = "当前条件下没有记录",
  children,
}: {
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <Database size={28} />
      <h3>{title}</h3>
      <div className="muted">
        {children || "调整查询条件，或在已有数据库中选择一条记录。"}
      </div>
    </div>
  );
}
export function QueryState({
  loading,
  error,
  retry,
}: {
  loading?: boolean;
  error?: string;
  retry: () => void;
}) {
  if (error)
    return (
      <div className="notice error" role="alert">
        <AlertCircle size={20} />
        <div>
          <strong>{error}</strong>
          <p>查询不会自动切换到样例数据。</p>
          <Button onClick={retry}>
            <RefreshCw size={15} />
            重试查询
          </Button>{" "}
          <Link to="/runs">返回运行记录</Link>
        </div>
      </div>
    );
  if (loading)
    return (
      <div role="status" aria-label="正在读取证据" className="skeleton">
        <span />
        <span />
        <span />
      </div>
    );
  return null;
}
export function SourceNote({ envelope }: { envelope: Envelope<unknown> }) {
  return (
    <details className="source-note">
      <summary>
        <Info size={14} />{" "}
        {envelope.source_kind === "fixture"
          ? "开发样例"
          : envelope.source_kind === "recorded_model_run"
            ? "历史实测"
            : "当前数据库"}{" "}
        · 来源详情
      </summary>
      <p>
        读取时间：{time(envelope.captured_at)} · 代码提交：
        {envelope.code_commit ?? "未提供"}
      </p>
      {envelope.missing_refs.length > 0 && (
        <p>缺失引用：{envelope.missing_refs.join("、")}</p>
      )}
      <p>
        记录用途与生成时间以原始证据为准；数据库来源不代表当前代码重新执行。
      </p>
    </details>
  );
}
export function Raw({
  value,
  title = "查看结构化记录",
}: {
  value: unknown;
  title?: string;
}) {
  return (
    <details className="raw">
      <summary>{title}</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}
export function PageTitle({
  title,
  description,
  actions,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="actions">{actions}</div>
    </div>
  );
}
export function EvidenceHint() {
  return (
    <div className="evidence-hint">
      <ShieldCheck size={18} />
      <span>每个结论，都有证据可循</span>
      <ArrowUpRight size={15} />
    </div>
  );
}
