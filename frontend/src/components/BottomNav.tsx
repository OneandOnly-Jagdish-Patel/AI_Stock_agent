import { NavLink, useLocation } from "react-router-dom";
import { moreMenuIcon, primaryNavItems } from "../config/nav";

interface Props {
  onMoreClick: () => void;
  moreActive: boolean;
}

export function BottomNav({ onMoreClick, moreActive }: Props) {
  const location = useLocation();

  return (
    <nav className="bottom-nav" aria-label="Mobile navigation">
      {primaryNavItems.map((item) => {
        const Icon = item.icon;
        const isActive =
          item.to === "/"
            ? location.pathname === "/"
            : location.pathname.startsWith(item.to);
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={`bottom-nav-item${isActive ? " active" : ""}`}
            aria-label={item.label}
            aria-current={isActive ? "page" : undefined}
          >
            <Icon size={22} aria-hidden />
            <span>{item.label}</span>
          </NavLink>
        );
      })}
      <button
        type="button"
        className={`bottom-nav-item${moreActive ? " active" : ""}`}
        onClick={onMoreClick}
        aria-label="More navigation options"
        aria-expanded={moreActive}
      >
        {(() => {
          const Icon = moreMenuIcon;
          return <Icon size={22} aria-hidden />;
        })()}
        <span>More</span>
      </button>
    </nav>
  );
}
