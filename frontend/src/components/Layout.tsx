import { NavLink, Outlet } from "react-router-dom";

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
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <h1>AI Trading Agent</h1>
          <p>Paper trading dashboard</p>
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
