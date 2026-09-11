import { useEffect, useMemo, useRef, useState } from "react";
import type { Run, TraceEvent } from "../../data/schema";
import {
  buildAgentSpans,
  formatDuration,
  formatTokens,
  type AgentSpan,
} from "./session-data";

interface GraphNode {
  id: string;
  role: string;
  x: number;
  y: number;
  step: string | null;
  status: string;
  tokens: { input: number | null; output: number | null };
  durationSeconds: number | null;
}

// 拓扑分层布局：上游在上，同层水平分布。
function layout(detail: Run): GraphNode[] {
  const edges = detail.edges ?? [];
  const nodes = detail.nodes ?? [];
  const depth = new Map<string, number>();
  const depthOf = (id: string, seen = new Set<string>()): number => {
    if (depth.has(id)) return depth.get(id)!;
    if (seen.has(id)) return 0;
    seen.add(id);
    const parents = edges.filter((e) => e.target === id).map((e) => e.source);
    const d = parents.length === 0 ? 0 : Math.max(...parents.map((p) => depthOf(p, seen))) + 1;
    depth.set(id, d);
    return d;
  };
  const withDepth = nodes.map((n) => ({ ...n, layer: depthOf(n.node_id) }));
  const layers = new Map<number, typeof withDepth>();
  for (const n of withDepth) {
    layers.set(n.layer, [...(layers.get(n.layer) ?? []), n]);
  }
  return withDepth.map((n) => {
    const peers = layers.get(n.layer) ?? [];
    const index = peers.findIndex((p) => p.node_id === n.node_id);
    const spread = peers.length === 1 ? 50 : 20 + (index * 60) / (peers.length - 1);
    return {
      id: n.node_id,
      role: n.role,
      x: spread,
      y: 14 + n.layer * 30,
      step: null,
      status: "queued",
      tokens: { input: null, output: null },
      durationSeconds: null,
    };
  });
}

export function TeamView({
  detail,
  events,
  activeNodeId,
  onSelectNode,
}: {
  detail: Run;
  events: TraceEvent[];
  activeNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
}) {
  const agents = useMemo(() => buildAgentSpans(detail, events), [detail, events]);
  const nodes = useMemo(() => {
    const base = layout(detail);
    return base.map((node) => {
      const own: AgentSpan[] = agents.filter((a) => a.nodeId === node.id);
      const tokens = own.reduce(
        (acc, a) => ({
          input: a.tokens.input ?? acc.input,
          output: a.tokens.output ?? acc.output,
        }),
        { input: null as number | null, output: null as number | null },
      );
      const durations = own
        .map((a) => a.durationSeconds)
        .filter((d): d is number => d !== null);
      const step =
        own.find((a) => a.summary)?.summary ??
        own.find((a) => a.action !== "等待上游")?.action ??
        null;
      const status = own.some((a) => a.status === "running")
        ? "running"
        : own.some((a) => a.status === "failed")
          ? "failed"
          : own.length > 0
            ? "completed"
            : "queued";
      return {
        ...node,
        step,
        status,
        tokens,
        durationSeconds:
          durations.length > 0
            ? durations.reduce((a, b) => a + b, 0)
            : null,
      };
    });
  }, [detail, agents]);

  const playback = useMemo(() => {
    const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
    return ordered
      .filter((e) => e.event_type === "agent_completed")
      .map((e) => ({
        node: e.node_id ?? "",
        edge:
          e.node_id && e.caused_by.length === 0
            ? null
            : `${e.node_id}`,
      }));
  }, [events]);
  const [index, setIndex] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const packetRef = useRef<SVGCircleElement>(null);
  const pathRefs = useRef<Map<string, SVGPathElement>>(new Map());
  const frameRef = useRef<number>(0);
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % Math.max(1, playback.length));
    }, 1450);
    return () => clearInterval(timer);
  }, [playing, playback.length]);
  useEffect(() => () => cancelAnimationFrame(frameRef.current), []);

  const activeEdge = useMemo(() => {
    if (index < 0 || index >= playback.length) return null;
    const target = playback[index].node;
    const edge = (detail.edges ?? []).find((e) => e.target === target);
    return edge ? `${edge.source}->${edge.target}` : null;
  }, [index, playback, detail.edges]);

  useEffect(() => {
    const path = activeEdge ? pathRefs.current.get(activeEdge) : null;
    const packet = packetRef.current;
    if (!path || !packet) return;
    const length = path.getTotalLength();
    const start = performance.now();
    const duration = 1050;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const point = path.getPointAtLength(length * t);
      packet.setAttribute("cx", String(point.x));
      packet.setAttribute("cy", String(point.y));
      if (t < 1) frameRef.current = requestAnimationFrame(tick);
    };
    if (reduced) {
      const point = path.getPointAtLength(length);
      packet.setAttribute("cx", String(point.x));
      packet.setAttribute("cy", String(point.y));
      return;
    }
    frameRef.current = requestAnimationFrame(tick);
  }, [activeEdge, index, reduced]);

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const activeNode = index >= 0 && index < playback.length ? playback[index].node : null;
  return (
    <div className="ws-team-view">
      <div className="ws-team-toolbar">
        <div className="ws-team-toolbar-left">
          <strong>团队组织</strong>
          <span className="ws-state-pill">
            <i />
            {detail.status === "completed" ? "已完成" : detail.status}
          </span>
          <span style={{ color: "var(--ws-muted)", fontSize: 11 }}>
            {nodes.length} Agents · {playback.length} 次交付
          </span>
        </div>
        <div className="ws-team-toolbar-right">
          <button
            type="button"
            className="ws-secondary-button"
            onClick={() => setIndex((i) => Math.max(0, i - 1))}
          >
            |‹
          </button>
          <button
            type="button"
            className="ws-secondary-button"
            onClick={() => setPlaying(!playing)}
          >
            {playing ? "Ⅱ 暂停" : "▶ 回放"}
          </button>
          <button
            type="button"
            className="ws-secondary-button"
            onClick={() => setIndex((i) => Math.min(playback.length - 1, i + 1))}
          >
            ›|
          </button>
        </div>
      </div>
      <div className="ws-graph-stage">
        <svg
          className="ws-graph-svg"
          viewBox="0 0 1000 580"
          preserveAspectRatio="none"
        >
          {(detail.edges ?? []).map((edge) => {
            const s = nodeMap.get(edge.source);
            const t = nodeMap.get(edge.target);
            if (!s || !t) return null;
            const x1 = s.x * 10;
            const y1 = s.y * 5.8 + 26;
            const x2 = t.x * 10;
            const y2 = t.y * 5.8 - 26;
            const midY = (y1 + y2) / 2;
            const key = `${edge.source}->${edge.target}`;
            return (
              <path
                key={key}
                ref={(el) => {
                  if (el) pathRefs.current.set(key, el);
                  else pathRefs.current.delete(key);
                }}
                className={`ws-graph-edge ${activeEdge === key ? "active" : ""} ${
                  edge.condition_ref ? "feedback" : ""
                }`}
                d={`M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`}
              />
            );
          })}
          <circle ref={packetRef} className="ws-packet" r={5} cx={-20} cy={-20} />
        </svg>
        {nodes.map((node) => (
          <button
            key={node.id}
            type="button"
            className={`ws-agent-node ${node.status} ${
              activeNode === node.id || activeNodeId === node.id ? "active" : ""
            }`}
            style={{ left: `${node.x}%`, top: `${node.y}%` }}
            onClick={() => onSelectNode(node.id)}
          >
            <div className="ws-node-top">
              <span className="ws-node-role">{node.role}</span>
              <span className="ws-node-status">
                <i className="ws-node-status-dot" />
                {node.status === "completed"
                  ? "Done"
                  : node.status === "running"
                    ? "Running"
                    : "Idle"}
              </span>
            </div>
            <div className="ws-node-task">
              {node.step ?? (detail.nodes ?? []).find((n) => n.node_id === node.id)?.role}
            </div>
            <div className="ws-node-metrics">
              {formatTokens(node.tokens)} · {formatDuration(node.durationSeconds)}
            </div>
          </button>
        ))}
        <div className="ws-graph-legend">
          <span>
            <i className="ws-legend-line active" />
            当前数据流
          </span>
          <span>
            <i className="ws-legend-line" />
            协作
          </span>
          <span>点击节点打开检查器</span>
        </div>
      </div>
    </div>
  );
}
