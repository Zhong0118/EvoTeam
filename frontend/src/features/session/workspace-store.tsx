/* Session workspace state — V3 §21: Context + useReducer, view/panel/
   selection mirrored into URL search params so refresh restores state (§24). */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import { useSearchParams } from "react-router-dom";

export type ActiveView = "chat" | "trace" | "team" | "evolution";
export type SidePanelKind =
  | "none"
  | "execution"
  | "artifact"
  | "agent-run"
  | "event";
export type GroupMode = "agent-run" | "turn" | "none";

export const SIDE_WIDTH = { default: 420, min: 340, max: 560 } as const;

export interface SessionWorkspaceState {
  sessionId: string;
  activeView: ActiveView;
  sidePanel: SidePanelKind;
  selectedAgentRunId?: string;
  selectedEventId?: string;
  selectedArtifactId?: string;
  followLatest: boolean;
  groupMode: GroupMode;
  manuallyClosedExecutionPanel: boolean;
  sideWidth: number;
}

type Action =
  | { type: "setView"; view: ActiveView }
  | { type: "setPanel"; panel: SidePanelKind }
  | { type: "toggleExecutionPanel" }
  | { type: "selectAgentRun"; agentRunId: string }
  | { type: "selectEvent"; eventId: string }
  | { type: "selectArtifact"; artifactId: string }
  | { type: "clearSelection" }
  | { type: "setFollowLatest"; value: boolean }
  | { type: "setGroupMode"; mode: GroupMode }
  | { type: "setSideWidth"; width: number };

const VIEWS: ActiveView[] = ["chat", "trace", "team", "evolution"];
const PANELS: SidePanelKind[] = [
  "none",
  "execution",
  "artifact",
  "agent-run",
  "event",
];
export const clampSideWidth = (w: number) =>
  Math.min(SIDE_WIDTH.max, Math.max(SIDE_WIDTH.min, w));

function reducer(state: SessionWorkspaceState, action: Action): SessionWorkspaceState {
  switch (action.type) {
    case "setView":
      return { ...state, activeView: action.view };
    case "setPanel":
      return {
        ...state,
        sidePanel: action.panel,
        manuallyClosedExecutionPanel:
          action.panel === "none" && state.sidePanel === "execution"
            ? true
            : action.panel === "execution"
              ? false
              : state.manuallyClosedExecutionPanel,
      };
    case "toggleExecutionPanel":
      return reducer(state, {
        type: "setPanel",
        panel: state.sidePanel === "execution" ? "none" : "execution",
      });
    case "selectAgentRun":
      return {
        ...state,
        sidePanel: "agent-run",
        selectedAgentRunId: action.agentRunId,
      };
    case "selectEvent":
      return { ...state, sidePanel: "event", selectedEventId: action.eventId };
    case "selectArtifact":
      return {
        ...state,
        sidePanel: "artifact",
        selectedArtifactId: action.artifactId,
      };
    case "clearSelection":
      return {
        ...state,
        sidePanel: "none",
        selectedAgentRunId: undefined,
        selectedEventId: undefined,
        selectedArtifactId: undefined,
      };
    case "setFollowLatest":
      return { ...state, followLatest: action.value };
    case "setGroupMode":
      return { ...state, groupMode: action.mode };
    case "setSideWidth":
      return { ...state, sideWidth: clampSideWidth(action.width) };
  }
}

function fromParams(
  sessionId: string,
  params: URLSearchParams,
): SessionWorkspaceState {
  const view = params.get("view") as ActiveView | null;
  const panel = params.get("panel") as SidePanelKind | null;
  return {
    sessionId,
    activeView: view && VIEWS.includes(view) ? view : "chat",
    sidePanel: panel && PANELS.includes(panel) ? panel : "none",
    selectedAgentRunId: params.get("agentRun") || undefined,
    selectedEventId: params.get("event") || undefined,
    selectedArtifactId: params.get("artifact") || undefined,
    followLatest: true,
    groupMode: "agent-run",
    manuallyClosedExecutionPanel: false,
    sideWidth: SIDE_WIDTH.default,
  };
}

const WorkspaceContext = createContext<{
  state: SessionWorkspaceState;
  dispatch: (action: Action) => void;
  onSessionChange: (id: string) => void;
} | null>(null);

export function SessionWorkspaceProvider({
  sessionId,
  children,
}: {
  sessionId: string;
  children: ReactNode;
}) {
  const [params, setParams] = useSearchParams();
  const [state, dispatch] = useReducer(
    reducer,
    { sessionId, params },
    ({ sessionId: id, params: p }) => fromParams(id, p),
  );

  // URL is the restore point for view/panel/selection (§24): rewrite on
  // state change, and re-read when the address itself changes (back/forward).
  useEffect(() => {
    const next = new URLSearchParams(params);
    next.set("view", state.activeView);
    if (state.sidePanel === "none") next.delete("panel");
    else next.set("panel", state.sidePanel);
    const pairs: [string, string | undefined][] = [
      ["agentRun", state.selectedAgentRunId],
      ["event", state.selectedEventId],
      ["artifact", state.selectedArtifactId],
    ];
    for (const [key, value] of pairs) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (next.toString() !== params.toString())
      setParams(next, { replace: true });
  }, [state, params, setParams]);

  const onSessionChange = useCallback(
    (id: string) => {
      const fresh = fromParams(id, new URLSearchParams());
      dispatch({ type: "setView", view: fresh.activeView });
    },
    [],
  );

  const value = useMemo(
    () => ({ state: { ...state, sessionId }, dispatch, onSessionChange }),
    [state, sessionId, onSessionChange],
  );
  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx)
    throw new Error("useWorkspace 必须在 SessionWorkspaceProvider 内使用");
  return ctx;
}
