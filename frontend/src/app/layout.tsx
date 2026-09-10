import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  Network,
  GitBranch,
  Layers3,
  Database,
  PanelLeftClose,
  Menu,
  ShieldCheck,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Sheet } from "../components/ui/sheet";
import { defaultStrategy, source } from "../data/client";
export function Layout() {
  const location = useLocation();
  const [menu, setMenu] = useState(false);
  const [info, setInfo] = useState(false);
  const run = location.pathname.match(/^\/runs\/([^/]+)/)?.[1];
  const strategy =
    new URLSearchParams(location.search).get("strategy_id") || defaultStrategy;
  const nav = [
    { to: "/runs", label: "运行记录", icon: Activity },
    {
      to: run ? `/runs/${run}/trace` : "/trace",
      label: "团队与 Trace",
      icon: Network,
    },
    { to: "/evolutions", label: "演进证据", icon: GitBranch },
    {
      to: strategy
        ? `/strategies/${encodeURIComponent(strategy)}`
        : "/strategies",
      label: "版本与指标",
      icon: Layers3,
    },
  ];
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        跳到内容
      </a>
      <aside className={`sidebar ${menu ? "is-open" : ""}`}>
        <NavLink className="brand" to="/runs" onClick={() => setMenu(false)}>
          <span className="brand-mark">
            <Network size={23} />
          </span>
          <span>
            Evo<span className="brand-accent">Team</span>
          </span>
        </NavLink>
        <div className="sidebar-caption">证据工作台</div>
        <nav aria-label="主导航">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={label}
              aria-label={label}
              to={to}
              className={({ isActive }) =>
                `nav-item ${isActive && !(to === "/runs" && location.pathname.endsWith("/trace")) ? "active" : ""}`
              }
              onClick={() => setMenu(false)}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <div className="sidebar-caption">运行与治理</div>
          <p>
            观察一次执行
            <br />
            理解每一次演进
          </p>
          <span className="tiny">Experience → Strategy</span>
        </div>
        <div className="sidebar-bottom">
          <Button variant="ghost" onClick={() => setInfo(true)}>
            <Database size={17} />
            <span>数据来源说明</span>
          </Button>
          <div className="local-note">
            <ShieldCheck size={13} /> 只读浏览 · 不调用模型
          </div>
        </div>
      </aside>
      {menu && (
        <button
          className="mobile-scrim"
          aria-label="收起导航"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="workspace">
        <header className="topbar">
          <div className="crumb">
            <Button
              size="icon"
              variant="ghost"
              className="menu-toggle"
              aria-label="打开导航"
              aria-expanded={menu}
              onClick={() => setMenu(!menu)}
            >
              <Menu size={20} />
            </Button>
            <PanelLeftClose size={16} className="desktop-icon" />
            <span>EvoTeam</span>
            <span className="muted">/</span>
            <strong>证据工作台</strong>
          </div>
          <button
            className={`source-chip ${source === "fixture" ? "fixture" : ""}`}
            onClick={() => setInfo(true)}
          >
            <span className="dot" />
            {source === "fixture" ? "开发样例 · 非实测" : "当前数据库"}
            <Database size={13} />
          </button>
        </header>
        <main id="main">
          <Outlet />
        </main>
        <footer>
          EVOTEAM <span>经验驱动的多智能体组织演进系统</span>
          <span>证据 → 验证 → 决定</span>
        </footer>
      </div>
      <Sheet
        open={info}
        onOpenChange={setInfo}
        title="数据来源说明"
        description="页面只读取已有证据。"
      >
        <p>
          {source === "fixture"
            ? "当前为明确选择的开发样例，用于检查页面与交互，不能用于报告真实实验结果。"
            : "当前通过只读 API 查询数据库；历史 Run 不等于当前代码重新运行。"}
        </p>
        <p>
          未知指标显示“未提供”。网络错误会显示原因，不会静默使用样例。正式服务版本以数据库当前引用为准。
        </p>
        <p>样例与 API 通过启动配置分别选择，切换后需重启前端。</p>
      </Sheet>
    </div>
  );
}
