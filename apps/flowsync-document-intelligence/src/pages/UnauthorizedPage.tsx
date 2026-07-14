import { fixedSafeClientError } from "../api/errors";
import { AccessScopeNotice } from "../components/AccessScopeNotice";
import { SafeErrorState } from "../components/SafeErrorState";

export function UnauthorizedPage() {
  return <div className="page-stack"><AccessScopeNotice /><SafeErrorState error={fixedSafeClientError("unauthorized")} /></div>;
}
