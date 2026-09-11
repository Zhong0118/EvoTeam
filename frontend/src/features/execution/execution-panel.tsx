/* Live Execution Graph — V3 §11. React Flow rendering of
   projectExecutionGraph(); compact mode shows AgentRun-level nodes with a
   3px status stripe. Follow-latest pauses on manual pan/zoom/select and can
   be resumed; node clicks locate the matching Chat row via the registry. */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  BackgroundVariant,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Crosshair, Group, Maximize2, WandSparkles } from "lucide-react";
import { flowKey } from "../runtime/types";
import { projectExecutionGraph, type ExecutionGraph } from "../runtime/projections";
import { locateFlowElement } from "../runtime/flow-registry";
import type { AgentEvent } from "../runtime/types";
import { ExecutionNode } from "./execution-node";
import { SidePanelHeader } from "./side-panels";
import { useLiveSession } from "../session/use-live-session";
import { useWorkspace } from "../session/workspace-store";

const NODE_W = 184;
const NODE_H = 66;
const GAP_X = 26;
const GAP_Y = 44;

function layeredLayout(graph: ExecutionGraph) {
  const depth = new Map<string, number>();
  const adj = new Map<string, string[]>();
  for (const n of graph.nodes) adj.set(n.id, []);
  for (const e of graph.edges) adj.get(e.source)?.push(e.target);
  if (graph.nodes.length) {
    const queue = [graph.nodes[0].id];
    depth.set(graph.nodes[0].id, 0);
    while (queue.length) {
      const id = queue.shift()!;
      for (const to of adj.get(id) ?? [])
        if (!depth.has(to)) {
          depth.set(to, (depth.get(id) ?? 0) + 1);
          queue.push(to);
        }
    }
  }
  const layers = new Map<number, string[]>();
  graph.nodes.forEach((n, i) => {
    const d = depth.get(n.id) ?? 0;
    const layer = layers.get(d);
    if (layer) layer.push(n.id);
    else layers.set(d, [n.id]);
    void i;
  });
  const position = new Map<string, { x: number; y: number }>();
  for (const [d, ids] of layers)
    ids.forEach((id, i) =>
      position.set(id, { x: i * (NODE_W + GAP_X), y: d * (NODE_H + GAP_Y) }),
    );
  return position;
}

function GraphCanvas({
  graph,
  follow,
  onUserMove,
  onSelect,
  selectedId,
}: {
  graph: ExecutionGraph;
  follow: boolean;
  onUserMove: () => void;
  onSelect: (id: string | null) => void;
  selectedId: string | null;
}) {
  const { setCenter, getZoom } = useReactFlow();
  const lastLatest = useRef<string | null>(null);

  useEffect(() => {
    if (!follow || !graph.latestNodeId) return;
    if (lastLatest.current === graph.latestNodeId) return;
    lastLatest.current = graph.latestNodeId;
    const node = graph.nodes.find((n) => n.id === graph.latestNodeId);
    const pos = layeredLayout(graph).get(graph.latestNodeId);
    if (!node || !pos) return;
    const zoom = Math.max(getZoom(), 0.7);
    setCenter(pos.x + NODE_W / 2, pos.y + NODE_H / 2, { zoom, duration: 420 });
  }, [follow, graph, setCenter, getZoom]);

  const position = useMemo(() => layeredLayout(graph), [graph]);
  const nodes: Node[] = graph.nodes.map((n) => ({
    id: n.id,
    type: "execution",
    position: position.get(n.id) ?? { x: 0, y: 0 },
    data: { ...n, selected: n.id === selectedId },
    draggable: false,
  }));
  const edges: Edge[] = graph.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: null,
    targetHandle: null,
    type: "default",
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: "#b9c7cf" },
    style:
      e.type === "feedback"
        ? { stroke: "#c58a22", strokeWidth: 1.4 }
        : e.type === "handoff"
          ? { stroke: "#8fa8b3", strokeWidth: 1.4 }
          : { stroke: "#cfdbe2", strokeWidth: 1.2 },
    animated: false,
  }));

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={{ execution: ExecutionNode }}
      onNodeClick={(_, node) => {
        onSelect(node.id);
        const data = node.data as {
          agentRunId?: string;
          eventId?: string;
          callId?: string;
          artifactId?: string;
        };
        // Same specificity order as ExecutionNode's data-flow-key, or a
        // Tool node (which carries agentRunId) would locate its owner row.
        const key = data.callId
          ? flowKey.tool(data.callId)
          : data.artifactId
            ? flowKey.artifact(data.artifactId)
            : data.agentRunId
              ? flowKey.agentRun(data.agentRunId)
              : data.eventId
                ? flowKey.event(data.eventId)
                : null;
        if (key) locateFlowElement(key, { onTimeout: () => selectNode(node.id) });
      }}
      onMove={(event) => {
        // Programmatic moves (fitView/setCenter) report a null event: they
        // must not cancel Follow Latest. Only a real drag/zoom pauses it.
        if (event) onUserMove();
      }}
      fitView
      minZoom={0.45}
      maxZoom={1.4}
      fitViewOptions={{ padding: 0.18 }}
      proOptions={{ hideAttribution: true }}
      nodesConnectable={false}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e0e6eb" />
    </ReactFlow>
  );

  function selectNode(id: string) {
    onSelect(id);
  }
}

export function ExecutionGraphView({ events }: { events: AgentEvent[] }) {
  const [hideTools, setHideTools] = useState(true);
  const [follow, setFollow] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [expandedRun, setExpandedRun] = useState<string | null>(null);
  const graph = useMemo(
    () =>
      projectExecutionGraph(events, {
        hideTools: hideTools && !expandedRun,
      }),
    [events, hideTools, expandedRun],
  );

  const resumeFollow = useCallback(() => setFollow(true), []);
  const pauseFollow = useCallback(() => setFollow(false), []);

  return (
    <div className="ws-graph-wrap">
      <div className="ws-graph-toolbar">
        <button
          className={`ws-tool-button ${follow ? "selected" : ""}`}
          title={follow ? "跟踪最新：开" : "跟踪最新：关"}
          aria-pressed={follow}
          onClick={follow ? pauseFollow : resumeFollow}
        >
          <Crosshair size={14} />
          {!follow && <span className="tiny">跟踪最新</span>}
        </button>
        <button className="ws-tool-button" title="分组：AgentRun（Trace 阶段扩展）" aria-disabled style={{ opacity: 0.45 }}>
          <Group size={14} />
        </button>
        <button
          className={`ws-tool-button ${!hideTools ? "selected" : ""}`}
          title={hideTools ? "显示工具节点" : "隐藏工具节点"}
          aria-pressed={!hideTools}
          onClick={() => setHideTools(!hideTools)}
        >
          <WandSparkles size={14} />
        </button>
        <button className="ws-tool-button" title="全屏（后续阶段）" aria-disabled style={{ opacity: 0.45 }}>
          <Maximize2 size={14} />
        </button>
      </div>
      <div className="ws-graph-canvas">
        <ReactFlowProvider>
          <GraphCanvas
            graph={graph}
            follow={follow}
            onUserMove={pauseFollow}
            onSelect={(id) => {
              setSelected(id);
              const node = graph.nodes.find((n) => n.id === id);
              setExpandedRun(node?.agentRunId && node.kind === "agent" ? node.agentRunId : null);
            }}
            selectedId={selected}
          />
        </ReactFlowProvider>
        {graph.nodes.length <= 1 && (
          <div className="ws-side-placeholder">正在创建执行图……</div>
        )}
      </div>
    </div>
  );
}

/* Panel chrome — V3 §11.3: 44px secondary switcher (执行图 | 产物 | ×),
   distinct from the main view tabs. */
export function ExecutionPanelView({ onClose }: { onClose: () => void }) {
  const { dispatch } = useWorkspace();
  const { events } = useLiveSession();
  return (
    <>
      <SidePanelHeader
        active="execution"
        onClose={onClose}
        onSelect={(kind) => dispatch({ type: "setPanel", panel: kind })}
      />
      <div className="ws-side-body" style={{ padding: 0, display: "grid" }}>
        <ExecutionGraphView events={events} />
      </div>
    </>
  );
}
