import { useState } from "react";
import { Outlet, useLocation, matchPath } from "react-router-dom";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { APP_ROUTES } from "./routes";

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const currentRoute = APP_ROUTES.find((route) =>
    matchPath({ path: route.path, end: true }, location.pathname),
  );

  return (
    <div className="app-frame">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="app-workspace">
        <Header
          title={currentRoute?.label ?? "Document Intelligence"}
          subtitle={currentRoute?.description ?? "Read-only workspace"}
          onMenuOpen={() => setSidebarOpen(true)}
        />
        <main className="main-content" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

