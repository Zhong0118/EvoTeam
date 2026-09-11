/* Contextual side panel — V2 §17/§18, V3 §12. One panel slot, content
   depends on the current selection. Full AgentRun Inspector and Event
   Inspector arrive with the Trace phase; until then these views show only
   facts the session projection already has — no fabricated context tabs. */
import { useMemo } from "react";
import { X } from "lucide-react";
import { useWorkspace, type SidePanelKind } from "../session/workspace-store";
import { useLiveSession } from "../session/use-live-session";
import { projectSession } from "../runtime/projections";
import { Badge } from "../../components/evidence/common";

export function SidePanelHeader({
  active,
  onSelect,
  onClose,
}: {
  active: SidePanelKind;
  onSelect: (kind: "execution" | "artifact") => void;
  onClose: () => void;
}) {
  return (
    <div className="ws-side-header">
      <div className="ws-side-tabs">
        <button
          className={`ws-side-tab ${active === "execution" ? "selected" : ""}`}
          onClick={() => onSelect("execution")}
        >
          执行图
        </button>
        <button
          className={`ws-side-tab ${active === "artifact" ? "selected" : ""}`}
          onClick={() => onSelect("artifact")}
        >
          产物
        </button>
      </div>
      <button className="ws-side-close" aria-label="关闭面板" onClick={onClose}>
        <X size={16} />
      </button>
    </div>
  );
}

export function SessionSidePanel() {
  const { state, dispatch } = useWorkspace();
  const { events } = useLiveSession();
  const session = useMemo(() => projectSession(events), [events]);
  const close = () => dispatch({ type: "setPanel", panel: "none" });
  const select = (kind: "execution" | "artifact") =>
    dispatch({ type: "setPanel", panel: kind });

  if (state.sidePanel === "artifact") {
    const artifacts = session.agentRuns.flatMap((run) =>
      run.outputArtifacts.map((id) => ({ id, run })),
    );
    return (
      <>
        <SidePanelHeader active="artifact" onSelect={select} onClose={close} />
        <div className="ws-side-body">
          {artifacts.length === 0 ? (
            <div className="ws-side-placeholder">任务产物将在生成后出现在这里</div>
          ) : (
            artifacts.map(({ id, run }) => (
              <div className="ws-artifact-row" key={id} style={{ width: "100%" }}>
                <span>{id}</span>
                <span className="tiny">{run.role}</span>
              </div>
            ))
          )}
          <p className="ws-side-note">
            内容预览需要 F1 持久化产物后接入；当前仅显示投影出的产物身份。
          </p>
        </div>
      </>
    );
  }
  if (state.sidePanel === "agent-run") {
    const run = session.agentRunById.get(state.selectedAgentRunId ?? "");
    if (!run)
      return (
        <>
          <SidePanelHeader active="none" onSelect={select} onClose={close} />
          <div className="ws-side-body">
            <div className="ws-side-placeholder">未选择运行实例</div>
          </div>
        </>
      );
    return (
      <>
        <SidePanelHeader active="agent-run" onSelect={select} onClose={close} />
        <div className="ws-side-body">
          <div className="ws-inspector-head">
            <strong>{run.role}</strong>
            <Badge value={run.status === "completed" ? "completed" : run.status} />
          </div>
          <dl className="metrics-list">
            <div><dt>AgentRun</dt><dd><code>{run.agentRunId}</code></dd></div>
            <div><dt>实例</dt><dd>{run.instanceId ?? "—"}</dd></div>
            <div><dt>工具调用</dt><dd>{run.toolCalls}</dd></div>
            <div><dt>Token</dt><dd>{run.tokens ?? "未提供"}</dd></div>
            <div><dt>耗时</dt><dd>{run.durationMs != null ? `${(run.durationMs / 1000).toFixed(1)}s` : "未知"}</dd></div>
          </dl>
          <p className="ws-side-note">
            过程 / 消息 / 产物 / 上下文四页 Inspector 依赖后端 agent_run_id
            落库（TASK_CORE R1/F1），此处不展示推测内容。
          </p>
        </div>
      </>
    );
  }
  return (
    <>
      <SidePanelHeader active="event" onSelect={select} onClose={close} />
      <div className="ws-side-body">
        <div className="ws-side-placeholder">
          Event Inspector 与完整轨迹视图在同一后续阶段交付
        </div>
      </div>
    </>
  );
}
