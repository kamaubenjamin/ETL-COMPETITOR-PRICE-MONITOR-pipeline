import { useEffect, useState } from "react";
import { Outlet, useLocation, matchPath } from "react-router-dom";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { APP_ROUTES } from "./routes";
import { hasValidDocumentIntelligenceApiConfiguration } from "../config/deploymentEnvironment";
import { fixedSafeClientError } from "../api/errors";
import { SafeErrorState } from "../components/SafeErrorState";

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const currentRoute = APP_ROUTES.find((route) =>
    matchPath({ path: route.path, end: true }, location.pathname),
  );
  const apiConfigurationValid = hasValidDocumentIntelligenceApiConfiguration();

  useEffect(() => {
    if (!sidebarOpen) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSidebarOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [sidebarOpen]);

  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="app-workspace">
        <Header
          title={currentRoute?.label ?? "Document Intelligence"}
          subtitle={currentRoute?.description ?? "Read-only workspace"}
          onMenuOpen={() => setSidebarOpen(true)}
          menuOpen={sidebarOpen}
        />
        <main className="main-content" id="main-content">
          {apiConfigurationValid
            ? <Outlet />
            : <SafeErrorState error={fixedSafeClientError("configuration")} />}
        </main>
      </div>
    </div>
  );
}
