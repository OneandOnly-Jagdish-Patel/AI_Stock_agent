import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";
import { fmtMoney } from "../utils/format";

const links = [
  { to: "/", label: "Overview" },
  { to: "/trades", label: "Trades & Reasons" },
  { to: "/signals", label: "AI Decisions" },
  { to: "/screener", label: "Screener" },
  { to: "/events", label: "Events & Briefings" },
  { to: "/history", label: "P&L History" },
  { to: "/logs", label: "Agent Logs" },
];

export function Layout() {
  const [equity, setEquity] = useState<number | null>(null);

  useEffect(() => {
    api
      .account()
      .then((a) => setEquity(a.equity ?? null))
      .catch(() => setEquity(null));
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <h1>AI Trading Agent</h1>
          <p>Paper trading dashboard</p>
          {equity != null && (
            <p className="mono" style={{ marginTop: "0.5rem", color: "var(--green)" }}>
              {fmtMoney(equity)}
            </p>
          )}
        </div>
        <nav>
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) =>
                `nav-link${isActive ? " active" : ""}`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
