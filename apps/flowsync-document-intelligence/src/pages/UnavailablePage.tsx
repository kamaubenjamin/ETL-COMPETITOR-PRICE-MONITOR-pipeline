import { fixedSafeClientError } from "../api/errors";
import { SafeErrorState } from "../components/SafeErrorState";
import { SafeAlert } from "../components/SafeAlert";
import { AlertTriangle, ShieldAlert } from "lucide-react";

export function UnavailablePage() {
  return <div className="page-stack">
    <SafeErrorState error={fixedSafeClientError("unavailable")} />
    <div className="safe-alert-grid">
      <SafeAlert icon={<AlertTriangle size={17} />} title="Runtime unavailable" message="Runtime availability is reported by the API. This UI cannot activate services." />
      <SafeAlert icon={<ShieldAlert size={17} />} title="Access configuration" message="An access configuration mismatch is handled outside this read-only application." />
      <SafeAlert title="Response validation" message="Data is withheld whenever an API response cannot be safely validated." />
    </div>
  </div>;
}
