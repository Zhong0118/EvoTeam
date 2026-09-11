/* SessionWorkspace page — routes /sessions and /sessions/:sessionId
   (V3 §24). Chat is implemented here (Phases 1–2); Trace / Team / Evolution
   stay honest placeholders until their own phases. The Live Execution Graph
   auto-open rule (V3 §11.1) lives with the view that owns the events. */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  SessionWorkspaceProvider,
  useWorkspace,
} from "../features/session/workspace-store";
import {
  LiveSessionProvider,
  useLiveSession,
  type LiveMode,
} from "../features/session/use-live-session";
import { SessionWorkspaceLayout } from "../app/session-workspace-layout";
import { ConversationView } from "../features/conversation/conversation-view";
import { defaultSessionId, sessionById } from "../fixtures/session";
import { scriptedUserTask } from "../fixtures/session-events";

function ViewPlaceholder({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="ws-static-view">
      <div className="ws-side-placeholder" style={{ height: "60vh" }}>
        <h2 style={{ fontSize: 15 }}>{title}</h2>
        <p>
          {phase}
          <br />
          当前轮次交付对话视图与实时执行图（V3 Phase 1–3）。
        </p>
      </div>
    </div>
  );
}

function SessionViews({ liveMode }: { liveMode: LiveMode }) {
  const { sessionId = defaultSessionId } = useParams();
  const { state, dispatch, onSessionChange } = useWorkspace();
  const { events, restart } = useLiveSession();
  const [userMessage, setUserMessage] = useState<string | null>(null);

  useEffect(() => {
    onSessionChange(sessionId);
    setUserMessage(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // V3 §11.1: the first runtime event auto-opens the Live Execution Graph on
  // desktop unless the user closed it for this session's run.
  const hasFirstEvent = events.length > 0;
  useEffect(() => {
    if (
      hasFirstEvent &&
      window.innerWidth >= 1280 &&
      !state.manuallyClosedExecutionPanel &&
      state.sidePanel === "none"
    )
      dispatch({ type: "setPanel", panel: "execution" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasFirstEvent]);

  // V3 §28: "new" is a real (empty) session, not a redirect to a sample.
  // sessionById("new") has no status, so liveMode is "idle" — no events
  // stream, the Hero empty state shows, and the Composer stays ready.

  const scriptedBubble =
    liveMode === "idle" ? null : userMessage ?? scriptedUserTask;

  return (
    <SessionWorkspaceLayout>
      {state.activeView === "chat" ? (
        <ConversationView
          userMessage={userMessage}
          scriptedUserTask={scriptedBubble}
          onSubmit={(text) => {
            // This round has no execution backend: a submission replays the
            // scripted sample so Chat and the Graph stay synchronized, and
            // the fixture Sheet states this explicitly.
            setUserMessage(text);
            restart();
          }}
        />
      ) : state.activeView === "trace" ? (
        <ViewPlaceholder title="轨迹视图" phase="完整流程图 / 时间线在 V3 Phase 4 交付" />
      ) : state.activeView === "team" ? (
        <ViewPlaceholder title="团队视图" phase="组织图 / 执行流 / 协作流在 V3 Phase 5 交付" />
      ) : (
        <ViewPlaceholder title="演进视图" phase="Strategy Diff / Trigger / Gate 在 V3 Phase 6 交付" />
      )}
    </SessionWorkspaceLayout>
  );
}

export function SessionWorkspace() {
  const { sessionId = defaultSessionId } = useParams();
  const summary = sessionById(sessionId);
  const liveMode: LiveMode =
    summary.status === "running"
      ? "replay"
      : summary.status === "completed"
        ? "completed"
        : "idle";
  return (
    <SessionWorkspaceProvider key={sessionId} sessionId={sessionId}>
      <LiveSessionProvider mode={liveMode}>
        <SessionViews liveMode={liveMode} />
      </LiveSessionProvider>
    </SessionWorkspaceProvider>
  );
}
