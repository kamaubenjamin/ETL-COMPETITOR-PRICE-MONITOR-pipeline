import { SafeErrorState } from "../components/SafeErrorState";

export function UnavailablePage() {
  return <SafeErrorState error={{ kind: "unavailable", code: "api_unavailable", message: "Document Intelligence is temporarily unavailable." }} />;
}

