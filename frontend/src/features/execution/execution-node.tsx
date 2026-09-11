/* Compact execution node — V3 §11.4: 184 wide, left status stripe, role +
   current step + tool/artifact counts. One shared node visual for the panel
   and (later) the full Trace graph. */
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { ExecutionGraphNode } from "../runtime/types";

const stripe = (kind: string, status: string) => {
  if (kind === "task") return "var(--muted)";
  if (kind === "tool" || kind === "verify") return "#c58a22";
  if (kind === "artifact") return "#387d66";
  switch (status) {
    case "running":
      return "var(--primary)";
    case "completed":
      return "#387d66";
    case "failed":
      return "#a14e45";
    default:
      return "#c9b98a";
  }
};

export function ExecutionNode({ data }: NodeProps) {
  const node = data as unknown as ExecutionGraphNode & { selected?: boolean };
  const label =
    node.kind === "task"
      ? "User Task"
      : node.kind === "artifact"
        ? "Artifact"
        : node.kind === "verify"
          ? "Verify"
          : node.kind === "tool"
            ? "Tool"
            : node.title;
  /* Most specific stable identity wins (V3 §11.7): a Tool node must not
     borrow its owning AgentRun's locate key. */
  const flowKey = node.callId
    ? `tool:${node.callId}`
    : node.artifactId
      ? `artifact:${node.artifactId}`
      : node.agentRunId
        ? `agent-run:${node.agentRunId}`
        : node.eventId
          ? `event:${node.eventId}`
          : undefined;
  return (
    <div
      className={`ws-exec-node ${node.selected ? "selected" : ""} ${
        node.kind === "task" ? "task" : ""
      }`}
      data-flow-key={flowKey}
    >
      <Handle type="target" position={Position.Top} />
      <span
        className="ws-exec-stripe"
        style={{ background: stripe(node.kind, node.status) }}
      />
      <div className="ws-exec-body">
        <div className="ws-exec-title">
          {label}
          {node.kind === "agent" && node.status === "running" && (
            <span className="ws-status-dot pulse" style={{ color: "var(--primary)" }} />
          )}
        </div>
        <div className="ws-exec-sub">{node.summary}</div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
