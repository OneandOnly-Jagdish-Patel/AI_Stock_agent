import { NavLink } from "react-router-dom";
import { fmtMoney } from "../utils/format";
import { navItems } from "../config/nav";

interface Props {
  equity: number | null;
}

export function Sidebar({ equity }: Props) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <h1>AI Trading Agent</h1>
        <p>Paper trading dashboard</p>
        {equity != null && (
          <div className="brand-equity">{fmtMoney(equity)}</div>
        )}
      </div>
      <nav aria-label="Main navigation">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `nav-link${isActive ? " active" : ""}`
              }
            >
              <Icon size={18} aria-hidden />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
