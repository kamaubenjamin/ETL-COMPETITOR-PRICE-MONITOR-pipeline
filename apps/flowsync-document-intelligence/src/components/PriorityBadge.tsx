import type { ReviewPriority } from "../types/review";

export function PriorityBadge({ priority }: { priority: ReviewPriority }) {
  return <span className={`priority-badge priority-badge--${priority}`}>{priority}</span>;
}
