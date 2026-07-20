import { Building2, Menu, ShieldCheck, UserRound } from "lucide-react";
import { deploymentEnvironmentLabel } from "../config/deploymentEnvironment";

interface HeaderProps {
  title: string;
  subtitle: string;
  onMenuOpen: () => void;
  menuOpen: boolean;
}

export function Header({ title, subtitle, onMenuOpen, menuOpen }: HeaderProps) {
  const environmentLabel = deploymentEnvironmentLabel();
  return (
    <header className="top-header">
      <div className="header-title-group">
        <button className="icon-button menu-button" type="button" onClick={onMenuOpen} aria-label="Open navigation" aria-controls="primary-sidebar" aria-expanded={menuOpen}>
          <Menu size={20} aria-hidden="true" />
        </button>
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
      </div>
      <div className="header-context" aria-label="Workspace context">
        <span className="environment-indicator" aria-label={`Deployment environment: ${environmentLabel}`}>{environmentLabel}</span>
        <span className="context-chip"><Building2 size={16} aria-hidden="true" /> Workspace unavailable</span>
        <span className="context-chip"><UserRound size={16} aria-hidden="true" /> Identity unavailable</span>
        <span className="security-indicator"><ShieldCheck size={16} aria-hidden="true" /> Read-only</span>
      </div>
    </header>
  );
}
