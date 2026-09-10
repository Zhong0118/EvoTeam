import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./app/layout";
import { Runs } from "./pages/runs";
import { RunDetail } from "./pages/run-detail";
const Trace = React.lazy(() =>
  import("./pages/trace").then((m) => ({ default: m.Trace })),
);
const EvolutionDetail = React.lazy(() =>
  import("./pages/evolutions").then((m) => ({ default: m.EvolutionDetail })),
);
const Evolutions = React.lazy(() =>
  import("./pages/evolutions").then((m) => ({ default: m.Evolutions })),
);
import { Strategies } from "./pages/strategies";
import { Empty } from "./components/evidence/common";
import "./styles/theme.css";
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
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/runs" replace />} />
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
            <Route path="*" element={<Empty title="页面不存在" />} />
          </Route>
        </Routes>
      </React.Suspense>
    </BrowserRouter>
  </React.StrictMode>,
);
