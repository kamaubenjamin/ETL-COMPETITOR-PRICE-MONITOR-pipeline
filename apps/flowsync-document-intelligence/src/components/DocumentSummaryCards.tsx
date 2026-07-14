import { CircleAlert, CircleCheck, FileStack, ScanLine, TriangleAlert } from "lucide-react";
import type { DocumentSummaryMetric } from "../types/viewModels";
import { StatusCard } from "./StatusCard";

const ICONS = {
  total: FileStack,
  active: ScanLine,
  review: CircleAlert,
  ready: CircleCheck,
  failed: TriangleAlert,
};

interface DocumentSummaryCardsProps {
  metrics: readonly DocumentSummaryMetric[];
}

export function DocumentSummaryCards({ metrics }: DocumentSummaryCardsProps) {
  return (
    <section className="status-grid status-grid--five" aria-label="Document status summary">
      {metrics.map((metric) => {
        const Icon = ICONS[metric.id];
        return (
          <StatusCard
            key={metric.id}
            label={metric.label}
            value={String(metric.value)}
            detail={metric.detail}
            tone={metric.tone}
            icon={<Icon size={18} aria-hidden="true" />}
          />
        );
      })}
    </section>
  );
}

