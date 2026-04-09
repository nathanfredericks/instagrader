import { Badge } from "@/components/ui/badge";
import type { AssignmentStatus } from "@/lib/types";

const statusConfig: Record<
  AssignmentStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; className?: string }
> = {
  draft: { label: "Draft", variant: "secondary" },
  grading: { label: "Grading", variant: "outline", className: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400 border-transparent" },
  review: { label: "Review", variant: "outline", className: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400 border-transparent" },
  completed: { label: "Completed", variant: "outline", className: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400 border-transparent" },
};

export function AssignmentStatusBadge({ status }: { status: AssignmentStatus }) {
  const config = statusConfig[status];
  return <Badge variant={config.variant} className={config.className}>{config.label}</Badge>;
}
