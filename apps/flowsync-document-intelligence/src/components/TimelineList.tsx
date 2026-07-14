import { History } from "lucide-react";
import { StatusChip } from "./StatusChip";

export interface TimelineItem {
  id: string;
  title: string;
  detail: string;
  timestamp: string;
  status?: string;
}

export function TimelineList({ items }: { items: readonly TimelineItem[] }) {
  return (
    <ol className="processing-timeline operational-timeline">
      {items.map((item) => (
        <li key={item.id}>
          <div className="timeline-marker"><History size={15} aria-hidden="true" /></div>
          <div><strong>{item.title}</strong><span>{item.detail}</span><time>{item.timestamp}</time></div>
          {item.status ? <StatusChip status={item.status} /> : null}
        </li>
      ))}
    </ol>
  );
}
