import React from "react";
import ReactDOM from "react-dom/client";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { Layout } from "./app/layout";
import { Session } from "./pages/session";
import { Runs } from "./pages/runs";
import { RunDetail } from "./pages/run-detail";
import { Trace } from "./pages/trace";
const EvolutionDetail = React.lazy(() =>
  import("./pages/evolutions").then((m) => ({ default: m.EvolutionDetail })),
);
const Evolutions = React.lazy(() =>
  import("./pages/evolutions").then((m) => ({ default: m.Evolutions })),
);
import { Strategies } from "./pages/strategies";
import { Empty } from "./components/evidence/common";
import "./styles/theme.css";
import "./styles/session.css";

// V2 规范 §20：旧一级路由保留为兼容跳转，实际页面归入 /dashboard 后台工作台。
function LegacyRedirect() {
  const location = useLocation();
  return (
    <Navigate
      to={`/dashboard${location.pathname}${location.search}`}
      replace
    />
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <React.Suspense
        fallback={
          <div role="status" className="empty">
            正在加载页面…
          </div>
        }
      >
        <Routes>
          <Route index element={<Session />} />
          <Route path="sessions/:sessionId" element={<Session />} />
          <Route path="dashboard" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard/runs" replace />} />
            <Route path="runs" element={<Runs />} />
            <Route path="runs/:runId" element={<RunDetail />} />
            <Route path="runs/:runId/trace" element={<Trace />} />
            <Route path="trace" element={<Trace />} />
            <Route path="evolutions" element={<Evolutions />} />
            <Route
              path="evolutions/:evolutionId"
              element={<EvolutionDetail />}
            />
            <Route path="strategies" element={<Strategies />} />
            <Route path="strategies/:strategyId" element={<Strategies />} />
          </Route>
          <Route path="runs/*" element={<LegacyRedirect />} />
          <Route path="trace" element={<LegacyRedirect />} />
          <Route path="evolutions/*" element={<LegacyRedirect />} />
          <Route path="strategies/*" element={<LegacyRedirect />} />
          <Route path="*" element={<Empty title="页面不存在" />} />
        </Routes>
      </React.Suspense>
    </BrowserRouter>
  </React.StrictMode>,
);
