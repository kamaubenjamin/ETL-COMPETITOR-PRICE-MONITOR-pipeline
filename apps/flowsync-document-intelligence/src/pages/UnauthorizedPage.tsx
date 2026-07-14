import { SafeErrorState } from "../components/SafeErrorState";

export function UnauthorizedPage() {
  return <SafeErrorState error={{ kind: "unauthorized", code: "unauthorized", message: "Sign in is required to continue." }} />;
}

