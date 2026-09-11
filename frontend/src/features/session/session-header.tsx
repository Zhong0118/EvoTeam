/* Topbar + View tabs — V3 §7/§8. 64px + 44px, filter-tab language, no
   breadcrumb wall. Strategy shows as a small badge; candidate reuses the
   existing purple semantics. */
import { Download, MoreHorizontal, PanelLeft } from "lucide-react";
import type { SessionSummary } from "../../fixtures/session";
import { useWorkspace, type ActiveView } from "./workspace-store";

const viewLabels: [ActiveView, string][] = [
  ["chat", "对话"],
  ["trace", "轨迹"],
  ["team", "团队"],
  ["evolution", "演进"],
];

export function SessionHeader({
  session,
  onToggleSidebar,
}: {
  session: SessionSummary;
  onToggleSidebar: () => void;
}) {
  const { state } = useWorkspace();
  return (
    <header className="ws-topbar">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          minWidth: 0,
        }}
      >
        <button
          className="ws-menu-toggle"
          aria-label="打开会话列表"
          onClick={onToggleSidebar}
        >
          <PanelLeft size={18} />
        </button>
        <h1 className="ws-task-title" title={session.title}>
          {session.title}
        </h1>
      </div>
      <div className="ws-topbar-right">
        <span className="ws-strategy-badge">Strategy v{session.strategyVersion}</span>
        <button className="ws-tool-button" aria-label="导出">
          <Download size={15} />
        </button>
        <button className="ws-tool-button" aria-label="更多操作">
          <MoreHorizontal size={16} />
        </button>
      </div>
      <span className="sr-only">当前视图：{state.activeView}</span>
    </header>
  );
}

export function SessionTabs() {
  const { state, dispatch } = useWorkspace();
  const chat = state.activeView === "chat";
  return (
    <nav className="ws-tabs" aria-label="视图切换">
      <div className="ws-tab-group">
        {viewLabels.map(([view, label]) => (
          <button
            key={view}
            className={`ws-tab ${
              state.activeView === view ? "selected" : ""
            } ${view === "evolution" ? "evolution" : ""}`}
            onClick={() => dispatch({ type: "setView", view })}
          >
            {label}
          </button>
        ))}
      </div>
      {chat && (
        <div className="ws-panel-toggles">
          <button
            className={`ws-panel-toggle ${
              state.sidePanel === "execution" ? "selected" : ""
            }`}
            onClick={() => dispatch({ type: "toggleExecutionPanel" })}
          >
            执行图
          </button>
          <button
            className={`ws-panel-toggle ${
              state.sidePanel === "artifact" ? "selected" : ""
            }`}
            onClick={() =>
              dispatch({
                type: "setPanel",
                panel: state.sidePanel === "artifact" ? "none" : "artifact",
              })
            }
          >
            产物
          </button>
        </div>
      )}
    </nav>
  );
}
