import type { components } from "@/lib/api/schema";

export type Assignment = components["schemas"]["Assignment"];
export type AssignmentList = components["schemas"]["AssignmentList"];
export type AssignmentStatus = components["schemas"]["AssignmentStatusEnum"];
export type Essay = components["schemas"]["Essay"];
export type EssayList = components["schemas"]["EssayList"];
export type EssayStatus = components["schemas"]["EssayStatusEnum"];
export type Rubric = components["schemas"]["Rubric"];
export type RubricList = components["schemas"]["RubricList"];
export type RubricCriterion = components["schemas"]["RubricCriterion"];
export type CriterionLevel = components["schemas"]["CriterionLevel"];
export type RubricTemplateSummary = components["schemas"]["RubricTemplateSummary"];
export type RubricConflictResponse = components["schemas"]["RubricConflictResponse"];
export type GradingResult = components["schemas"]["GradingResult"];
export type CriterionScore = components["schemas"]["CriterionScore"];
export type CriterionScoreUpdate = components["schemas"]["CriterionScoreUpdate"];
export type CriterionScoreReviewState =
  components["schemas"]["TeacherReviewStateEnum"];
export type DashboardResponse = components["schemas"]["DashboardResponse"];
export type RecentActivityItem = components["schemas"]["RecentActivityItem"];
