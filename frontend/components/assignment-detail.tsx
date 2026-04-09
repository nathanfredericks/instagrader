"use client";

import useSWR from "swr";
import { client } from "@/lib/api/client";
import { GradingProgressView } from "@/components/grading-progress-view";
import { ReviewView } from "@/components/review-view";
import { CompletedView } from "@/components/completed-view";
import type { Assignment, Rubric } from "@/lib/types";

export function AssignmentDetail({
  assignmentId,
  initialAssignment,
  initialRubric,
}: {
  assignmentId: string;
  initialAssignment: Assignment;
  initialRubric: Rubric | undefined;
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

  if (!assignment) return null;

  return (
    <>
      {(assignment.status === "draft" || assignment.status === "grading") && (
        <GradingProgressView
          assignmentId={assignmentId}
          essays={assignment.essays}
          assignmentStatus={assignment.status}
          gradingStartedAt={assignment.grading_started_at ?? null}
        />
      )}
      {assignment.status === "review" && (
        <ReviewView assignmentId={assignmentId} essays={assignment.essays} />
      )}
      {assignment.status === "completed" && rubric && (
        <CompletedView assignment={assignment} rubric={rubric} />
      )}
    </>
  );
}
