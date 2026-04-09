"use client";

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Check, CheckIcon, ChevronLeft, ChevronRight, Loader2Icon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { client } from "@/lib/api/client";
import { buildRubricLookup } from "@/lib/rubric";
import type {
  CriterionScoreReviewState,
  Essay,
  EssayList,
  EssayStatus,
  Rubric,
  GradingResult,
} from "@/lib/types";
import { EssayTextPanel } from "@/components/essay-text-panel";
import { CriterionScoreCard } from "@/components/criterion-score-card";
import { ReviewNavigation } from "@/components/review-navigation";

interface EssayReviewProps {
  assignmentId: string;
  essayId: string;
  essays: EssayList[];
  rubric: Rubric;
  initialEssay: Essay | undefined;
  initialGrading: GradingResult | undefined;
}

type CriterionSessionState = {
  aiLevel: string;
  selectedLevel: string;
  feedback: string;
  reviewState: CriterionScoreReviewState;
  dirty: boolean;
};

const statusConfig: Record<
  EssayStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  pending: { label: "Pending", variant: "secondary" },
  processing: { label: "Processing", variant: "default" },
  graded: { label: "Ready for Review", variant: "outline" },
  reviewed: { label: "Reviewed", variant: "secondary" },
  failed: { label: "Failed", variant: "destructive" },
};

// reconstructs review state from grading data, backend stores it across multiple fields
function inferReviewState(
  score: GradingResult["criterion_scores"][number],
  isEssayReviewed: boolean
): CriterionScoreReviewState {
  if (score.teacher_review_state) {
    return score.teacher_review_state;
  }
  if (score.teacher_level) {
    return "overridden";
  }
  return isEssayReviewed ? "accepted_ai" : "pending";
}

function buildCriterionSession(
  grading: GradingResult | null
): Record<string, CriterionSessionState> {
  if (!grading) return {};
  const isEssayReviewed = grading.teacher_approved;
  return Object.fromEntries(
    grading.criterion_scores.map((score) => {
      const reviewState = inferReviewState(score, isEssayReviewed);
      return [
        score.id,
        {
          aiLevel: score.level,
          selectedLevel: score.teacher_level ?? score.level,
          feedback: score.teacher_feedback ?? "",
          reviewState,
          dirty: false,
        } satisfies CriterionSessionState,
      ];
    })
  );
}

export function EssayReview({
  assignmentId,
  essayId,
  essays,
  rubric,
  initialEssay,
  initialGrading,
}: EssayReviewProps) {
  const router = useRouter();
  const [currentEssayId, setCurrentEssayId] = useState(essayId);
  const [essay, setEssay] = useState<Essay | null>(initialEssay ?? null);
  const [grading, setGrading] = useState<GradingResult | null>(
    initialGrading ?? null
  );
  const [loading, setLoading] = useState(!initialEssay);
  const [transitioning, setTransitioning] = useState(false);
  const [finalizeState, setFinalizeState] = useState<"idle" | "saving">(
    "idle"
  );
  const [draftSaveStatus, setDraftSaveStatus] = useState<"idle" | "pending" | "saving" | "saved" | "error">("idle");
  const [mobileTab, setMobileTab] = useState<"essay" | "scoring">("essay");
  const [criterionSession, setCriterionSession] = useState<
    Record<string, CriterionSessionState>
  >(() => buildCriterionSession(initialGrading ?? null));

  // ref mirrors state so async save callbacks dont capture stale closures
  const criterionSessionRef = useRef(criterionSession);
  const draftSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    criterionSessionRef.current = criterionSession;
  }, [criterionSession]);

  const rubricLookup = useMemo(() => buildRubricLookup(rubric), [rubric]);

  useEffect(() => {
    if (currentEssayId === essayId && initialEssay && initialGrading) {
      return;
    }

    let cancelled = false;

    async function fetchData() {
      setTransitioning(true);
      setFinalizeState("idle");
      setDraftSaveStatus("idle");
      setMobileTab("essay");

      try {
        const [essayRes, gradingRes] = await Promise.all([
          client.GET("/api/essays/{essay_id}/", {
            params: { path: { essay_id: currentEssayId } },
          }),
          client.GET("/api/essays/{essay_id}/grading/", {
            params: { path: { essay_id: currentEssayId } },
          }),
        ]);

        if (cancelled) return;

        if (essayRes.data) setEssay(essayRes.data);
        if (gradingRes.data) {
          setGrading(gradingRes.data);
          setCriterionSession(buildCriterionSession(gradingRes.data));
        }
      } catch {
        if (!cancelled) {
          toast.error("Failed to load essay review data.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setTransitioning(false);
          window.scrollTo({ top: 0, behavior: "instant" });
        }
      }
    }

    void fetchData();
    return () => {
      cancelled = true;
    };
  }, [currentEssayId, essayId, initialEssay, initialGrading]);

  const currentIndex = essays.findIndex((e) => e.id === currentEssayId);
  const prevEssay = currentIndex > 0 ? essays[currentIndex - 1] : null;
  const nextEssay = currentIndex < essays.length - 1 ? essays[currentIndex + 1] : null;
  const isApproved = grading?.teacher_approved ?? false;

  const sortedScores = useMemo(() => {
    if (!grading) return [];
    return [...grading.criterion_scores].sort((a, b) => {
      const orderA = rubricLookup.get(a.criterion)?.order ?? 0;
      const orderB = rubricLookup.get(b.criterion)?.order ?? 0;
      return orderA - orderB;
    });
  }, [grading, rubricLookup]);

  const allCriteriaReviewed =
    sortedScores.length > 0 &&
    sortedScores.every(
      (score) => criterionSession[score.id]?.reviewState !== "pending"
    );
  const canFinalize = !isApproved && allCriteriaReviewed;

  const navigateToEssay = useCallback(
    (targetEssayId: string) => {
      window.history.pushState(
        null,
        "",
        `/assignments/${assignmentId}/essays/${targetEssayId}`
      );
      window.scrollTo({ top: 0, behavior: "instant" });
      setCurrentEssayId(targetEssayId);
    },
    [assignmentId]
  );

  const updateCriterionSession = useCallback(
    (
      criterionScoreId: string,
      updater: (state: CriterionSessionState) => CriterionSessionState
    ) => {
      setCriterionSession((prev) => {
        const existing = prev[criterionScoreId];
        if (!existing) return prev;
        return {
          ...prev,
          [criterionScoreId]: { ...updater(existing), dirty: true },
        };
      });
    },
    []
  );

  const handleReviewStateChange = useCallback(
    (criterionScoreId: string, reviewState: CriterionScoreReviewState) => {
      updateCriterionSession(criterionScoreId, (state) => {
        const nextSelectedLevel =
          reviewState === "overridden" ? state.selectedLevel : state.aiLevel;
        return {
          ...state,
          reviewState,
          selectedLevel: nextSelectedLevel,
        };
      });
    },
    [updateCriterionSession]
  );

  const handleOverrideLevelChange = useCallback(
    (criterionScoreId: string, levelId: string) => {
      updateCriterionSession(criterionScoreId, (state) => ({
        ...state,
        selectedLevel: levelId,
        reviewState: "overridden",
      }));
    },
    [updateCriterionSession]
  );

  const handleFeedbackChange = useCallback(
    (criterionScoreId: string, feedback: string) => {
      updateCriterionSession(criterionScoreId, (state) => ({
        ...state,
        feedback,
      }));
    },
    [updateCriterionSession]
  );

  // only saves criteria that have been touched, skips pending ones
  const handleAutosave = useCallback(async () => {
    const session = criterionSessionRef.current;
    const dirtyScores = Object.entries(session).filter(
      ([, s]) => s.dirty && s.reviewState !== "pending"
    );
    if (dirtyScores.length === 0) return;

    setDraftSaveStatus("saving");
    const { error } = await client.PATCH("/api/essays/{essay_id}/grading/", {
      params: { path: { essay_id: currentEssayId } },
      body: {
        criterion_scores: dirtyScores.map(([id, s]) => ({
          id,
          teacher_review_state: s.reviewState,
          teacher_level: s.reviewState === "overridden" ? s.selectedLevel : null,
          teacher_feedback: s.feedback,
        })),
      },
    });

    if (error) {
      setDraftSaveStatus("error");
      return;
    }

    setCriterionSession((prev) => {
      const next = { ...prev };
      for (const [id] of dirtyScores) {
        if (next[id]) next[id] = { ...next[id], dirty: false };
      }
      return next;
    });
    setDraftSaveStatus("saved");
  }, [currentEssayId]);

  useEffect(() => {
    if (isApproved) return;
    const hasDirtyNonPending = Object.values(criterionSession).some(
      (s) => s.dirty && s.reviewState !== "pending"
    );
    if (!hasDirtyNonPending) return;
    if (draftSaveTimerRef.current) clearTimeout(draftSaveTimerRef.current);
    setDraftSaveStatus("pending");
    draftSaveTimerRef.current = setTimeout(() => {
      void handleAutosave();
    }, 1000);
    return () => {
      if (draftSaveTimerRef.current) clearTimeout(draftSaveTimerRef.current);
    };
  }, [criterionSession]);

  // checks all criteria reviewed before posting approval, then navigates to next unreviewed essay
  const handleFinalize = useCallback(async () => {
    if (isApproved) return;
    setFinalizeState("saving");

    const hasPendingCriteria = sortedScores.some(
      (score) => criterionSessionRef.current[score.id]?.reviewState === "pending"
    );
    if (hasPendingCriteria) {
      setFinalizeState("idle");
      toast.error("Review every criterion before saving.");
      return;
    }

    const { data, error } = await client.POST(
      "/api/essays/{essay_id}/grading/approve/",
      {
        params: { path: { essay_id: currentEssayId } },
        body: {
          criterion_scores: sortedScores.map((score) => {
            const session = criterionSessionRef.current[score.id];
            return {
              id: score.id,
              teacher_review_state: session.reviewState,
              teacher_level:
                session.reviewState === "overridden"
                  ? session.selectedLevel
                  : null,
              teacher_feedback: session.feedback,
            };
          }),
        },
      }
    );

    if (error || !data) {
      setFinalizeState("idle");
      toast.error("Unable to finalize this essay.");
      return;
    }

    setGrading(data);
    setCriterionSession(buildCriterionSession(data));
    setFinalizeState("idle");

    const nextUnreviewed = essays.find(
      (e, index) => index > currentIndex && e.status !== "reviewed"
    );
    if (nextUnreviewed) {
      navigateToEssay(nextUnreviewed.id);
    } else {
      router.push(`/assignments/${assignmentId}`);
    }
  }, [
    assignmentId,
    currentEssayId,
    currentIndex,
    essays,
    isApproved,
    navigateToEssay,
    router,
    sortedScores,
  ]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading essay...</p>
      </div>
    );
  }

  if (!essay || !grading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Essay or grading data not found.</p>
      </div>
    );
  }

  return (
    <div
      className="space-y-6 transition-opacity duration-200 pb-24 lg:pb-0"
      style={{ opacity: transitioning ? 0.5 : 1 }}
    >
      {/* Desktop sticky toolbar */}
      <header className="sticky top-0 z-10 -mx-4 lg:-mx-6 px-4 lg:px-6 bg-background/95 backdrop-blur border-b hidden lg:flex items-center justify-between gap-4 py-2">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/assignments/${assignmentId}`)}
          >
            <ArrowLeft className="size-4" />
            Back
          </Button>
          <h1 className="text-base font-semibold truncate">{essay.file_name}</h1>
          {essay.status && (
            <Badge variant={statusConfig[essay.status].variant}>
              {statusConfig[essay.status].label}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            disabled={!prevEssay || finalizeState !== "idle"}
            onClick={() => prevEssay && navigateToEssay(prevEssay.id)}
          >
            <ChevronLeft className="size-4" />
            Previous
          </Button>
          <span className="text-muted-foreground text-sm tabular-nums px-1">
            {currentIndex + 1} of {essays.length}
          </span>
          {!isApproved && draftSaveStatus === "saving" && (
            <span className="text-muted-foreground text-sm flex items-center gap-1.5">
              <Loader2Icon className="size-3.5 animate-spin" />
              Saving...
            </span>
          )}
          {!isApproved && draftSaveStatus === "saved" && (
            <span className="text-muted-foreground text-sm flex items-center gap-1.5">
              <CheckIcon className="size-3.5" />
              Saved
            </span>
          )}
          {!isApproved && draftSaveStatus === "error" && (
            <span className="text-amber-600 text-sm">Save failed</span>
          )}
          {isApproved ? (
            <Button variant="outline" size="sm" disabled>
              <Check className="size-4" />
              Approved
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={handleFinalize}
              disabled={!canFinalize || finalizeState !== "idle"}
            >
              <Check className="size-4" />
              {finalizeState === "saving" ? "Saving..." : "Approve & Next"}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            disabled={!nextEssay || finalizeState !== "idle"}
            onClick={() => nextEssay && navigateToEssay(nextEssay.id)}
          >
            Next
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </header>

      {/* Mobile header (nav handled by fixed bottom bar) */}
      <div className="flex items-center gap-4 lg:hidden">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push(`/assignments/${assignmentId}`)}
        >
          <ArrowLeft className="size-4" />
          Back
        </Button>
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <h1 className="text-lg font-semibold truncate">{essay.file_name}</h1>
          <span className="text-muted-foreground text-sm shrink-0">
            {currentIndex + 1} of {essays.length}
          </span>
          {essay.status && (
            <Badge variant={statusConfig[essay.status].variant}>
              {statusConfig[essay.status].label}
            </Badge>
          )}
        </div>
      </div>

      <div className="hidden lg:grid lg:grid-cols-2 gap-6">
        <EssayTextPanel
          extractedText={essay.extracted_text}
          assignmentId={assignmentId}
          essayId={currentEssayId}
        />

        <div className="space-y-4">
          {sortedScores.map((score) => {
            const criterion = rubricLookup.get(score.criterion);
            if (!criterion) return null;

            const state = criterionSession[score.id];
            if (!state) return null;

            return (
              <div key={score.id}>
                <CriterionScoreCard
                  criterionScoreId={score.id}
                  criterionName={criterion.name}
                  levels={criterion.levels}
                  aiLevel={score.level}
                  aiFeedback={score.feedback}
                  selectedLevel={state.selectedLevel}
                  feedback={state.feedback}
                  reviewState={state.reviewState}
                  isReviewed={isApproved}
                  onReviewStateChange={(reviewState) =>
                    handleReviewStateChange(score.id, reviewState)
                  }
                  onLevelChange={(levelId) =>
                    handleOverrideLevelChange(score.id, levelId)
                  }
                  onFeedbackChange={(feedback) =>
                    handleFeedbackChange(score.id, feedback)
                  }
                />
              </div>
            );
          })}
        </div>
      </div>

      <div className="lg:hidden">
        <Tabs value={mobileTab} onValueChange={(value) => setMobileTab(value as "essay" | "scoring")}>
          <TabsList className="w-full">
            <TabsTrigger value="essay">Essay</TabsTrigger>
            <TabsTrigger value="scoring">Scoring</TabsTrigger>
          </TabsList>

          <TabsContent value="essay" className="pt-4">
            <EssayTextPanel
              extractedText={essay.extracted_text}
              assignmentId={assignmentId}
              essayId={currentEssayId}
            />
          </TabsContent>

          <TabsContent value="scoring" className="pt-4 space-y-4">
            {sortedScores.map((score) => {
              const criterion = rubricLookup.get(score.criterion);
              if (!criterion) return null;
              const state = criterionSession[score.id];
              if (!state) return null;

              return (
                <div key={score.id}>
                  <CriterionScoreCard
                    criterionScoreId={score.id}
                    criterionName={criterion.name}
                    levels={criterion.levels}
                    aiLevel={score.level}
                    aiFeedback={score.feedback}
                    selectedLevel={state.selectedLevel}
                    feedback={state.feedback}
                    reviewState={state.reviewState}
                    isReviewed={isApproved}
                    onReviewStateChange={(reviewState) =>
                      handleReviewStateChange(score.id, reviewState)
                    }
                    onLevelChange={(levelId) =>
                      handleOverrideLevelChange(score.id, levelId)
                    }
                    onFeedbackChange={(feedback) =>
                      handleFeedbackChange(score.id, feedback)
                    }
                  />
                </div>
              );
            })}
          </TabsContent>
        </Tabs>
      </div>

      <div className="hidden lg:block">
        <ReviewNavigation
          essayId={currentEssayId}
          essays={essays}
          isApproved={isApproved}
          onFinalize={handleFinalize}
          onNavigate={navigateToEssay}
          canFinalize={canFinalize}
          finalizeState={finalizeState}
          saveStatus={draftSaveStatus}
          navigationDisabled={finalizeState !== "idle"}
        />
      </div>

      <div className="lg:hidden fixed bottom-0 left-0 right-0 border-t bg-background/95 backdrop-blur p-3">
        <ReviewNavigation
          essayId={currentEssayId}
          essays={essays}
          isApproved={isApproved}
          onFinalize={handleFinalize}
          onNavigate={navigateToEssay}
          canFinalize={canFinalize}
          finalizeState={finalizeState}
          saveStatus={draftSaveStatus}
          navigationDisabled={finalizeState !== "idle"}
        />
      </div>
    </div>
  );
}
