import { NavLink, useLocation } from "react-router-dom";
import { X } from "lucide-react";
import { moreNavItems } from "../config/nav";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function MoreMenu({ open, onClose }: Props) {
  const location = useLocation();

  if (!open) return null;

  return (
    <>
      <div
        className="more-overlay"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        role="presentation"
        aria-hidden
      />
      <div className="more-sheet" role="dialog" aria-label="More navigation">
        <div className="more-sheet-header">
          <h3>More</h3>
          <button
            type="button"
            className="more-sheet-close"
            onClick={onClose}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>
        <div className="more-sheet-links">
          {moreNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`more-sheet-link${isActive ? " active" : ""}`}
                onClick={onClose}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon size={20} aria-hidden />
                {item.label}
              </NavLink>
            );
          })}
        </div>
      </div>
    </>
  );
}
