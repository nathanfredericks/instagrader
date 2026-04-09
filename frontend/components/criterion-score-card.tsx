"use client";

import { Check } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { CriterionScoreReviewState } from "@/lib/types";
import type { LevelLookup } from "@/lib/rubric";

interface CriterionScoreCardProps {
  criterionScoreId: string;
  criterionName: string;
  levels: Map<string, LevelLookup>;
  aiLevel: string;
  aiFeedback: string;
  selectedLevel: string;
  feedback: string;
  reviewState: CriterionScoreReviewState;
  isReviewed: boolean;
  onReviewStateChange: (state: CriterionScoreReviewState) => void;
  onLevelChange: (levelId: string) => void;
  onFeedbackChange: (feedback: string) => void;
}

export function CriterionScoreCard({
  criterionScoreId,
  criterionName,
  levels,
  aiLevel,
  aiFeedback,
  selectedLevel,
  feedback,
  reviewState,
  isReviewed,
  onReviewStateChange,
  onLevelChange,
  onFeedbackChange,
}: CriterionScoreCardProps) {
  const aiLevelInfo = levels.get(aiLevel);
  const selectedLevelInfo = levels.get(selectedLevel);
  // sorted descending by score so highest appears first in dropdown
  const sortedLevels = Array.from(levels.entries()).sort(
    (a, b) => b[1].score - a[1].score
  );

  const levelSelectId = `${criterionScoreId}-override-level`;
  const feedbackId = `${criterionScoreId}-feedback`;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <div className="flex items-center gap-2 min-w-0">
          <CardTitle className="text-base">{criterionName}</CardTitle>
          {reviewState === "accepted_ai" && (
            <Badge className="bg-green-100 text-green-700 border border-green-200 shrink-0">
              Accepted
            </Badge>
          )}
          {reviewState === "overridden" && (
            <Badge className="bg-amber-100 text-amber-700 border border-amber-200 shrink-0">
              Override
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="bg-muted/50 rounded-md p-3 space-y-2">
          <div className="space-y-0.5">
            <span className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
              Automated Score
            </span>
            {aiLevelInfo && (
              <div className="flex items-start gap-2 text-sm">
                <span className="inline-flex items-center justify-center size-6 rounded border border-border text-xs font-semibold shrink-0">
                  {aiLevelInfo.score}
                </span>
                <span className="text-muted-foreground">{aiLevelInfo.descriptor}</span>
              </div>
            )}
          </div>
          {aiFeedback && (
            <details>
              <summary className="text-xs text-muted-foreground cursor-pointer select-none">
                Show Thinking
              </summary>
              <p className="text-muted-foreground text-sm mt-2">{aiFeedback}</p>
            </details>
          )}
        </div>

        {isReviewed ? (
          <div className="space-y-1.5">
            <span className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
              Teacher Review
            </span>
            {reviewState === "overridden" && selectedLevelInfo && (
              <p className="text-sm">
                <span className="font-semibold">{selectedLevelInfo.score}</span> —{" "}
                {selectedLevelInfo.descriptor}
              </p>
            )}
            {feedback && <p className="text-muted-foreground text-sm">{feedback}</p>}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex gap-2">
              <Button
                variant={reviewState === "accepted_ai" ? "default" : "outline"}
                size="sm"
                className="flex-1"
                onClick={() => onReviewStateChange("accepted_ai")}
              >
                <Check className="size-3.5" />
                Accept
              </Button>
              <Button
                variant={reviewState === "overridden" ? "default" : "outline"}
                size="sm"
                className="flex-1"
                onClick={() => onReviewStateChange("overridden")}
              >
                Override
              </Button>
            </div>

            {reviewState === "overridden" && (
              <div className="space-y-1.5">
                <label
                  htmlFor={levelSelectId}
                  className="text-muted-foreground text-xs font-medium uppercase tracking-wide"
                >
                  Override Score
                </label>
                <Select value={selectedLevel} onValueChange={onLevelChange}>
                  <SelectTrigger id={levelSelectId} className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {sortedLevels.map(([id, level]) => (
                      <SelectItem key={id} value={id}>
                        {level.score} - {level.descriptor}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-1.5">
              <label
                htmlFor={feedbackId}
                className="text-muted-foreground text-xs font-medium uppercase tracking-wide"
              >
                Feedback
              </label>
              <Textarea
                id={feedbackId}
                value={feedback}
                onChange={(e) => onFeedbackChange(e.target.value)}
                placeholder="Add teacher feedback..."
                rows={3}
              />
            </div>

          </div>
        )}
      </CardContent>
    </Card>
  );
}
