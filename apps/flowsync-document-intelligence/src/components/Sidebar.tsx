import {
  FileStack,
  ListChecks,
  ScrollText,
  Settings2,
  Workflow,
  X,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { NAVIGATION_ROUTES, type RouteId } from "../app/routes";

const ICONS: Partial<Record<RouteId, LucideIcon>> = {
  documents: FileStack,
  review: ListChecks,
  workflows: Workflow,
  audit: ScrollText,
  "runtime-preview": Settings2,
};

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      <button
        className={`sidebar-scrim ${open ? "sidebar-scrim--visible" : ""}`}
        type="button"
        aria-label="Close navigation"
        onClick={onClose}
      />
      <aside className={`sidebar ${open ? "sidebar--open" : ""}`} aria-label="Primary navigation" id="primary-sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark" aria-hidden="true">F</div>
          <div>
            <strong>FlowSync</strong>
            <span>Document Intelligence</span>
          </div>
          <button className="icon-button sidebar-close" type="button" onClick={onClose} aria-label="Close navigation">
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <nav className="sidebar-nav">
          <span className="nav-section-label">Workspace</span>
          {NAVIGATION_ROUTES.map((route) => {
            const Icon = ICONS[route.id] ?? FileStack;
            return (
              <NavLink
                key={route.id}
                className={({ isActive }) => `nav-link ${isActive ? "nav-link--active" : ""}`}
                to={route.path}
                onClick={onClose}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{route.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-foot">
          <span className="read-only-dot" aria-hidden="true" />
          <div>
            <strong>Read-only foundation</strong>
            <span>API authority preserved</span>
          </div>
        </div>
      </aside>
    </>
  );
}
