import { useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { api } from "../api/client";
import { moreNavItems } from "../config/nav";
import { BottomNav } from "./BottomNav";
import { MoreMenu } from "./MoreMenu";
import { Sidebar } from "./Sidebar";

export function Layout() {
  const [equity, setEquity] = useState<number | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);

  const moreActive = moreNavItems.some((item) =>
    location.pathname.startsWith(item.to),
  );

  useEffect(() => {
    api
      .account()
      .then((a) => setEquity(a.equity ?? null))
      .catch(() => setEquity(null));
  }, []);

  useEffect(() => {
    setMoreOpen(false);
    mainRef.current?.focus();
  }, [location.pathname]);

  return (
    <div className="layout">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <Sidebar equity={equity} />
      <main
        id="main-content"
        ref={mainRef}
        className="main"
        tabIndex={-1}
      >
        <Outlet />
      </main>
      <BottomNav
        onMoreClick={() => setMoreOpen((o) => !o)}
        moreActive={moreActive || moreOpen}
      />
      <MoreMenu open={moreOpen} onClose={() => setMoreOpen(false)} />
    </div>
  );
}
