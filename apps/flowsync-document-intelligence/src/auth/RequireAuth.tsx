import { Outlet } from "react-router-dom";
import { SafeErrorState } from "../components/SafeErrorState";
import { fixedSafeClientError } from "../api/errors";
import { SignInPage } from "../pages/SignInPage";
import { useAuth } from "./useAuth";
import { deploymentEnvironmentLabel } from "../config/deploymentEnvironment";

export function RequireAuth() {
  const { status, signOut } = useAuth();
  const label = <span className="environment-indicator">{deploymentEnvironmentLabel()}</span>;
  if (status === "loading") return <div className="auth-status" role="status">{label}Restoring your secure session…</div>;
  if (status === "configuration_error") {
    return <div className="auth-status">{label}<SafeErrorState error={fixedSafeClientError("auth_configuration")} /></div>;
  }
  if (status === "unauthorized") {
    return <div className="auth-status">{label}<SafeErrorState error={fixedSafeClientError("forbidden")} /><button type="button" className="secondary-button" onClick={() => void signOut()}>Sign out</button></div>;
  }
  if (status !== "authenticated") return <SignInPage />;
  return <Outlet />;
}
