import { useMemo } from "react";
import {
  Background,
  Controls,
  MarkerType,
  Position,
  ReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Run, TraceEvent } from "../../data/schema";
import {
  buildAgentRuns,
  buildCollaboration,
} from "../runtime/projection";

// V2 规范 §11/§13：Team 视图 = 图谱 + 协作流；数据与 Chat/Trace 同源（run detail + events）。
export function TeamView({
  detail,
  events,
  compact,
}: {
  detail: Run;
  events: TraceEvent[];
  compact: boolean;
}) {
  const agents = useMemo(() => buildAgentRuns(detail, events), [detail, events]);
  const feed = useMemo(() => buildCollaboration(events), [events]);
  const graphNodes = (detail.nodes ?? []).map((n, i) => {
    const agent = agents.find((a) => a.nodeId === n.node_id);
    return {
      id: n.node_id,
      position: compact ? { x: 30, y: i * 170 } : { x: i * 240, y: 60 },
      sourcePosition: compact ? Position.Bottom : Position.Right,
      targetPosition: compact ? Position.Top : Position.Left,
      data: {
        label: (
          <div className="team-node">
            <span className="node-role">{n.role.toUpperCase()}</span>
            <strong>{n.node_id}</strong>
            <span className="team-node-step">
              {agent?.step ?? "—"}
            </span>
            <span className="tiny">
              {agent
                ? `${agent.messages.length} 条消息 · 状态 ${agent.status}`
                : "无执行实例"}
            </span>
          </div>
        ),
      },
      draggable: false,
      connectable: false,
      style: { width: 190 },
    };
  });
  const graphEdges = (detail.edges ?? []).map((e, i) => ({
    id: `edge-${i}`,
    source: e.source,
    target: e.target,
    markerEnd: { type: MarkerType.ArrowClosed },
    animated: agents.some(
      (a) => a.nodeId === e.source && a.step === "产物沿连边交付下游",
    ),
    label: e.condition_ref ? "条件路由" : undefined,
    style: e.condition_ref ? { strokeDasharray: "5 5" } : undefined,
  }));
  return (
    <div className="team-columns">
      <div className="team-graph">
        {graphNodes.length ? (
          <ReactFlow
            key={compact ? "m" : "d"}
            nodes={graphNodes}
            edges={graphEdges}
            fitView
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            minZoom={0.25}
            maxZoom={1.5}
          >
            <Background color="#dce4e8" gap={20} />
            <Controls showInteractive={false} />
          </ReactFlow>
        ) : (
          <p className="tiny">该记录未提供完整配置拓扑。</p>
        )}
      </div>
      <div className="team-feed">
        <h4>协作流</h4>
        {feed.length === 0 ? (
          <p className="tiny">该记录没有已保存的协作事件。</p>
        ) : (
          feed.map((item) => (
            <div
              className={`feed-item ${item.kind}`}
              key={item.key}
            >
              <strong>{item.nodeId ?? "系统"}</strong>
              <span>{item.text}</span>
              {item.detail && <small>{item.detail}</small>}
              <time>{item.timestamp.slice(11, 19)}</time>
            </div>
          ))
        )}
        <p className="tiny">
          协作流按事件顺序展示节点交接；真实耗时以轨迹视图为准。
        </p>
      </div>
    </div>
  );
}
