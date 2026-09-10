import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  Background,
  Controls,
  MarkerType,
  Position,
  ReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  ArrowLeft,
  Pause,
  Play,
  SkipBack,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Sheet } from "../components/ui/sheet";
import {
  Badge,
  Empty,
  PageTitle,
  Panel,
  QueryState,
  Raw,
  SourceNote,
  time,
} from "../components/evidence/common";
import { RunTrack } from "../components/evidence/run-track";
import { useEvidence } from "../data/client";
import { eventsSchema, runSchema } from "../data/schema";
const names: Record<string, string> = {
  agent_started: "开始执行",
  agent_completed: "执行完成",
  agent_failed: "执行失败",
  agent_message: "传递消息",
  team_created: "创建团队",
  task_created: "创建任务",
  run_finished: "运行结束",
  evaluation_completed: "评价完成",
  run_sealed: "证据封存",
  tool_called: "调用工具",
  tool_result: "工具结果",
};
export function Trace() {
  const [compact, setCompact] = useState(
    () => window.matchMedia("(max-width: 767px)").matches,
  );
  useEffect(() => {
    const media = window.matchMedia("(max-width: 767px)");
    const update = () => setCompact(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  const { runId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const query = useEvidence(
    runId ? `/runs/${encodeURIComponent(runId)}` : null,
    runSchema,
  );
  const events = useEvidence(
    runId ? `/runs/${encodeURIComponent(runId)}/events` : null,
    eventsSchema,
  );
  const [playing, setPlaying] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const r = query.value?.data;
  const list = useMemo(
    () =>
      [...(events.value?.data.items ?? [])].sort(
        (a, b) => a.sequence - b.sequence,
      ),
    [events.value],
  );
  const selectedId = params.get("event");
  const index = Math.max(
    0,
    list.findIndex((e) => e.event_id === selectedId),
  );
  const selected = list[index];
  const nodeId = params.get("node") || selected?.node_id;
  const instanceId = params.get("instance") || selected?.instance_id;
  const node = r?.nodes?.find((n) => n.node_id === nodeId);
  const instances = r?.instances?.filter((i) => i.node_id === nodeId) ?? [];
  const instance =
    instances.find((i) => i.instance_id === instanceId) || instances[0];
  function select(n: number) {
    const event = list[n];
    if (!event) return;
    const p = new URLSearchParams(params);
    p.set("event", event.event_id);
    if (event.node_id) p.set("node", event.node_id);
    else p.delete("node");
    if (event.instance_id) p.set("instance", event.instance_id);
    else p.delete("instance");
    setParams(p, { replace: true });
  }
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      const next = Math.min(index + 1, list.length - 1);
      if (next === index) {
        setPlaying(false);
        return;
      }
      const e = list[next];
      const p = new URLSearchParams();
      p.set("event", e.event_id);
      if (e.node_id) p.set("node", e.node_id);
      if (e.instance_id) p.set("instance", e.instance_id);
      setParams(p, { replace: true });
    }, 600);
    return () => clearInterval(timer);
  }, [playing, index, list, setParams]);
  useEffect(() => () => setPlaying(false), [runId]);
  const graphNodes = (r?.nodes ?? []).map((n, i) => ({
    id: n.node_id,
    position: compact ? { x: 30, y: i * 185 } : { x: i * 255, y: 70 },
    sourcePosition: compact ? Position.Bottom : Position.Right,
    targetPosition: compact ? Position.Top : Position.Left,
    data: {
      label: (
        <div className="agent-node">
          <span className="node-role">{n.role.toUpperCase()}</span>
          <strong>{n.node_id}</strong>
          <span>
            {r?.instances?.filter((x) => x.node_id === n.node_id).length ?? 0}{" "}
            个执行实例
          </span>
        </div>
      ),
    },
    selected: n.node_id === nodeId,
    draggable: false,
    connectable: false,
    style: { width: 200 },
  }));
  const graphEdges = (r?.edges ?? []).map((e, i) => {
    const next = playing ? list[index + 1] : undefined;
    const currentEvent = playing ? list[index] : undefined;
    const flowing =
      playing &&
      !!currentEvent?.node_id &&
      !!next?.node_id &&
      currentEvent.node_id !== next.node_id &&
      e.source === currentEvent.node_id &&
      e.target === next.node_id;
    return {
      id: `edge-${i}`,
      source: e.source,
      target: e.target,
      markerEnd: { type: MarkerType.ArrowClosed },
      animated: flowing,
      label: e.condition_ref ? "条件路由" : undefined,
      style: e.condition_ref ? { strokeDasharray: "5 5" } : undefined,
    };
  });
  return (
    <>
      <Link
        className="back-link"
        to={runId ? `/runs/${encodeURIComponent(runId)}` : "/runs"}
      >
        <ArrowLeft size={14} /> {runId ? "任务详情" : "运行记录"}
      </Link>
      <PageTitle
        title="团队与执行证据"
        description={
          runId
            ? `${runId} · 固定配置与实际执行分别呈现`
            : "选择一条运行记录，查看团队如何完成任务。"
        }
      />
      {!runId ? (
        <Empty title="尚未选择 Run">
          <Link to="/runs">前往运行记录选择 →</Link>
        </Empty>
      ) : (
        <>
          <QueryState {...query} retry={query.refresh} />
          {r && (
            <>
              <div className="record-strip">
                <Badge>Strategy v{r.strategy.version}</Badge>
                <Badge value={r.status} />
                <span className="tiny">
                  配置节点 {r.nodes?.length ?? 0} · 执行实例{" "}
                  {r.instances?.length ?? 0}
                </span>
              </div>
              <div className="trace-columns">
                <Panel
                  title="团队拓扑"
                  aside={<span className="tiny">只读 · 可缩放与平移</span>}
                >
                  <div className="graph-canvas">
                    {graphNodes.length ? (
                      <ReactFlow
                        key={`${runId}-${compact}`}
                        nodes={graphNodes}
                        edges={graphEdges}
                        fitView
                        nodesDraggable={false}
                        nodesConnectable={false}
                        elementsSelectable
                        onNodeClick={(_, n) => {
                          setPlaying(false);
                          const p = new URLSearchParams(params);
                          p.set("node", n.id);
                          p.delete("instance");
                          setParams(p, { replace: true });
                          setDrawer(true);
                        }}
                        minZoom={0.25}
                        maxZoom={1.5}
                      >
                        <Background color="#dce4e8" gap={20} />
                        <Controls showInteractive={false} />
                      </ReactFlow>
                    ) : (
                      <Empty title="未提供完整配置拓扑" />
                    )}
                  </div>
                  <div className="graph-legend">
                    <span className="dot" /> 配置节点 <span>→ 信息流</span>
                    <span>右侧轨道展示实际执行次序与结果</span>
                  </div>
                </Panel>
                <Panel
                  title="运行轨道"
                  aside={
                    <>
                      <Badge>{list.length} 步</Badge>
                      {playing && <Badge value="执行中" />}
                    </>
                  }
                >
                  <QueryState {...events} retry={events.refresh} />
                  {events.value && list.length > 0 && (
                    <RunTrack
                      events={list}
                      activeIndex={index}
                      streaming={playing}
                      onSelect={(e) => {
                        setPlaying(false);
                        const i = list.findIndex(
                          (item) => item.event_id === e.event_id,
                        );
                        if (i >= 0) select(i);
                        setDrawer(true);
                      }}
                    />
                  )}
                  {events.value && list.length === 0 && (
                    <Empty title="该运行没有可用事件" />
                  )}
                </Panel>
              </div>
              <div className="playback">
                <div className="actions">
                  <Badge>历史回放</Badge>
                  <Button
                    size="icon"
                    aria-label="回到开始"
                    disabled={!list.length}
                    onClick={() => {
                      setPlaying(false);
                      select(0);
                    }}
                  >
                    <SkipBack size={17} />
                  </Button>
                  <Button
                    size="icon"
                    aria-label="上一步"
                    disabled={!list.length || index === 0}
                    onClick={() => {
                      setPlaying(false);
                      select(index - 1);
                    }}
                  >
                    <ChevronLeft size={17} />
                  </Button>
                  <Button
                    variant="default"
                    disabled={!list.length}
                    onClick={() => {
                      if (index === list.length - 1) select(0);
                      setPlaying(!playing);
                    }}
                  >
                    {playing ? <Pause size={16} /> : <Play size={16} />}{" "}
                    {playing ? "暂停" : "播放"}
                  </Button>
                  <Button
                    size="icon"
                    aria-label="下一步"
                    disabled={!list.length || index === list.length - 1}
                    onClick={() => {
                      setPlaying(false);
                      select(index + 1);
                    }}
                  >
                    <ChevronRight size={17} />
                  </Button>
                </div>
                <span className="tiny">
                  {list.length ? `${index + 1} / ${list.length} · ` : ""}每步
                  600ms · 示意节奏，非实际耗时
                </span>
              </div>
              <SourceNote envelope={query.value!} />
            </>
          )}
        </>
      )}
      <Sheet
        open={drawer}
        onOpenChange={setDrawer}
        title={node ? `${node.role} · 执行证据` : "系统事件"}
        description="按配置和实例查看已保存的证据。"
      >
        {node && (
          <>
            <div className="record-strip">
              <Badge>{node.config_id}</Badge>
            </div>
            <p>
              Prompt：{node.prompt_ref.id}@{node.prompt_ref.version}
            </p>
            <label className="field-label">
              执行实例
              <select
                value={instance?.instance_id || ""}
                onChange={(e) => {
                  const p = new URLSearchParams(params);
                  p.set("instance", e.target.value);
                  setParams(p, { replace: true });
                }}
              >
                {instances.map((i) => (
                  <option key={i.instance_id} value={i.instance_id}>
                    {i.instance_id}
                  </option>
                ))}
              </select>
            </label>
            {instance && (
              <>
                <Badge value={instance.state} />
                <h3>输入来源</h3>
                {instance.messages.map((m) => (
                  <div className="notice" key={m.message_id}>
                    <p>
                      {m.sender_node_id || "原始任务"} → {m.recipient_node_id}
                    </p>
                    <small>
                      {m.source_event_ids.join("、") || "无来源事件引用"}
                    </small>
                  </div>
                ))}
                <p className="tiny">
                  输入任务见任务详情。原始运行上下文与输入载荷不导出。
                </p>
                <h3>结构化输出</h3>
                <Raw value={instance.output} title="展开此实例输出" />
              </>
            )}
          </>
        )}
        {selected && (
          <>
            <h3>选中事件</h3>
            <p>
              {names[selected.event_type] || selected.event_type} ·{" "}
              {time(selected.timestamp)}
            </p>
            <p className="tiny">
              因果来源：{selected.caused_by.join("、") || "无"}
            </p>
            <Raw value={selected} />
          </>
        )}
      </Sheet>
    </>
  );
}
