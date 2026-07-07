import type { LucideIcon } from "lucide-react";
import {
  ArrowLeftRight,
  BrainCircuit,
  Calendar,
  Radio,
  LayoutDashboard,
  Menu,
  ScrollText,
  Settings,
  TrendingUp,
} from "lucide-react";

export type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  mobilePrimary?: boolean;
  mobileMore?: boolean;
};

export const navItems: NavItem[] = [
  { to: "/", label: "Overview", icon: LayoutDashboard, mobilePrimary: true },
  { to: "/trades", label: "Trades", icon: ArrowLeftRight, mobilePrimary: true },
  { to: "/signals", label: "Signals", icon: BrainCircuit, mobilePrimary: true },
  { to: "/history", label: "History", icon: TrendingUp, mobilePrimary: true },
  { to: "/screener", label: "Screener", icon: Calendar, mobileMore: true },
  { to: "/events", label: "Events", icon: Radio, mobileMore: true },
  { to: "/logs", label: "Logs", icon: ScrollText, mobileMore: true },
  { to: "/admin", label: "Admin", icon: Settings, mobileMore: true },
];

export const primaryNavItems = navItems.filter((i) => i.mobilePrimary);
export const moreNavItems = navItems.filter((i) => i.mobileMore);
export const moreMenuIcon = Menu;
