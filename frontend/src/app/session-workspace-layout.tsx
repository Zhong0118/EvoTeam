/* SessionWorkspaceLayout — V3 §5–§12. Own shell, never the legacy dashboard
   layout: body does not scroll, each region owns its scroll, and the right
   panel is a single Contextual Side Panel (V2 §17) shared by Chat/Trace. */
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Sheet } from "../components/ui/sheet";
import { useWorkspace } from "../features/session/workspace-store";
import { SessionSidebar } from "../features/session/session-sidebar";
import { SessionHeader, SessionTabs } from "../features/session/session-header";
import { ExecutionPanelView } from "../features/execution/execution-panel";
import { SessionSidePanel } from "../features/execution/side-panels";
import { sessionById } from "../fixtures/session";

export function SessionWorkspaceLayout({ children }: { children: ReactNode }) {
  const { state, dispatch } = useWorkspace();
  const session = sessionById(state.sessionId);
  const [mobileNav, setMobileNav] = useState(false);
  const [info, setInfo] = useState(false);
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ x: number; width: number } | null>(null);

  // V3 §11.2: drag on the 1px divider (4px hit area); pointer capture keeps
  // the gesture alive even if the cursor escapes the handle.
  const onPointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.currentTarget.setPointerCapture(event.pointerId);
      drag.current = { x: event.clientX, width: state.sideWidth };
      setDragging(true);
    },
    [state.sideWidth],
  );
  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!drag.current) return;
      dispatch({
        type: "setSideWidth",
        width: drag.current.width - (event.clientX - drag.current.x),
      });
    },
    [dispatch],
  );
  const endDrag = useCallback(() => {
    drag.current = null;
    setDragging(false);
  }, []);

  const panelOpen = state.sidePanel !== "none";
  useEffect(() => {
    document.body.classList.toggle("ws-noscroll", panelOpen);
    return () => document.body.classList.remove("ws-noscroll");
  }, [panelOpen]);

  return (
    <div className={`ws-shell ${panelOpen ? "panel-open" : ""}`}>
      <SessionSidebar
        mobileOpen={mobileNav}
        onNavigate={() => setMobileNav(false)}
        onOpenInfo={() => {
          setMobileNav(false);
          setInfo(true);
        }}
      />
      {mobileNav && (
        <button
          className="ws-scrim visible"
          aria-label="收起会话列表"
          onClick={() => setMobileNav(false)}
        />
      )}
      <div className="ws-main">
        <SessionHeader
          session={session}
          onToggleSidebar={() => setMobileNav(!mobileNav)}
        />
        <SessionTabs />
        <div className="ws-content">
          {children}
          {panelOpen && (
            <>
              <div
                className={`ws-resizer ${dragging ? "dragging" : ""}`}
                role="separator"
                aria-orientation="vertical"
                aria-label="调整右栏宽度"
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
              />
              <aside
                className="ws-side-panel"
                style={{ width: state.sideWidth }}
              >
                {state.sidePanel === "execution" ? (
                  <ExecutionPanelView
                    onClose={() => dispatch({ type: "setPanel", panel: "none" })}
                  />
                ) : (
                  <SessionSidePanel />
                )}
              </aside>
            </>
          )}
        </div>
      </div>
      <Sheet
        open={info}
        onOpenChange={setInfo}
        title="数据来源说明"
        description="工作区当前为开发样例。"
      >
        <p>
          本 Workspace 的会话与执行事件是 fixture 开发样例，用于检查布局与交互，
          不能用于报告真实实验结果。只读证据请使用「高级 · 证据工作台」。
        </p>
        <p>执行入口（POST /v1/executions）与 SSE 实时流接入前，输入任务只会重放开演样例。</p>
      </Sheet>
    </div>
  );
}
