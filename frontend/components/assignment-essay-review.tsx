"use client";

import useSWR from "swr";
import { client } from "@/lib/api/client";
import { EssayReview } from "@/components/essay-review";
import type { Assignment, Essay, GradingResult, Rubric } from "@/lib/types";

export function AssignmentEssayReview({
  assignmentId,
  essayId,
  initialAssignment,
  initialRubric,
  initialEssay,
  initialGrading,
}: {
  assignmentId: string;
  essayId: string;
  initialAssignment: Assignment;
  initialRubric: Rubric | undefined;
  initialEssay: Essay | undefined;
  initialGrading: GradingResult | undefined;
}) {
  const { data: assignment } = useSWR(
    `/api/assignments/${assignmentId}/`,
    async () => {
      const { data } = await client.GET("/api/assignments/{assignment_id}/", {
        params: { path: { assignment_id: assignmentId } },
      });
      return data;
    },
    { fallbackData: initialAssignment, refreshInterval: 5000 }
  );

  const { data: rubric } = useSWR(
    assignment?.rubric ? `/api/rubrics/${assignment.rubric}/` : null,
    async () => {
      const { data } = await client.GET("/api/rubrics/{rubric_id}/", {
        params: { path: { rubric_id: assignment!.rubric } },
      });
      return data;
    },
    { fallbackData: initialRubric, refreshInterval: 5000 }
  );

  if (!assignment || !rubric) {
    return (
      <div className="py-8">
        <p className="text-muted-foreground text-sm">
          Essay review data is not available.
        </p>
      </div>
    );
  }

  return (
    <EssayReview
      assignmentId={assignmentId}
      essayId={essayId}
      essays={assignment.essays}
      rubric={rubric}
      initialEssay={initialEssay}
      initialGrading={initialGrading}
    />
  );
}
