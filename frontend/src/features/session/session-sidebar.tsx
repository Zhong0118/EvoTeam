/* Session sidebar — V3 §6. Fixed 206px. Primary nav is Sessions only;
   Run/Evolution/Strategy evidence lives at the bottom as Advanced access. */
import { Link, useNavigate } from "react-router-dom";
import {
  Database,
  FolderGit2,
  History,
  Network,
  Plus,
  Settings,
} from "lucide-react";
import { sessions } from "../../fixtures/session";
import { useWorkspace } from "./workspace-store";

const statusLabel = {
  running: "运行中",
  completed: "已完成",
  queued: "排队",
} as const;

export function SessionSidebar({
  onOpenInfo,
  mobileOpen,
  onNavigate,
}: {
  onOpenInfo: () => void;
  mobileOpen: boolean;
  onNavigate: () => void;
}) {
  const { state } = useWorkspace();
  const navigate = useNavigate();
  return (
    <aside className={`ws-sidebar ${mobileOpen ? "is-open" : ""}`}>
      <div className="ws-brand">
        <span className="ws-brand-mark">
          <Network size={16} />
        </span>
        <span>EvoTeam</span>
      </div>
      <button
        className="ws-new-session"
        onClick={() => {
          onNavigate();
          navigate("/sessions/new");
        }}
      >
        <Plus size={15} /> 新会话
      </button>
      <div className="ws-caption">工作区</div>
      <div className="ws-workspace-row">
        <FolderGit2 size={14} />
        <span>EvoTeam · project-planning</span>
      </div>
      <div className="ws-caption">会话</div>
      <nav className="ws-session-list" aria-label="会话列表">
        {sessions.map((session) => (
          <button
            key={session.sessionId}
            className={`ws-session-row ${
              session.sessionId === state.sessionId ? "active" : ""
            }`}
            onClick={() => {
              onNavigate();
              navigate(`/sessions/${session.sessionId}`);
            }}
          >
            <span className="ws-session-main">
              <span className="ws-session-title" title={session.title}>
                {session.title}
              </span>
              <span className="ws-session-sub">{session.sub}</span>
            </span>
            <span
              className={`ws-session-status ${
                session.status === "running" ? "running" : ""
              }`}
            >
              {session.status === "running" && (
                <span className="ws-status-dot pulse" />
              )}
              {statusLabel[session.status]}
            </span>
          </button>
        ))}
      </nav>
      <div className="ws-sidebar-bottom">
        <Link className="ws-bottom-link" to="/runs" onClick={onNavigate}>
          <History size={14} /> 高级 · 证据工作台
        </Link>
        <button className="ws-bottom-link" onClick={onOpenInfo}>
          <Database size={14} /> 数据来源说明
        </button>
        <button className="ws-bottom-link" onClick={onNavigate}>
          <Settings size={14} /> 设置
        </button>
      </div>
    </aside>
  );
}
