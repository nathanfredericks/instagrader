"use client";

import { Button } from "@/components/ui/button";
import { Check, CheckIcon, ChevronLeft, ChevronRight, Loader2Icon } from "lucide-react";
import type { EssayList } from "@/lib/types";

interface ReviewNavigationProps {
  essayId: string;
  essays: EssayList[];
  isApproved: boolean;
  onFinalize: () => void;
  onNavigate: (essayId: string) => void;
  canFinalize: boolean;
  finalizeState: "idle" | "saving";
  saveStatus: "idle" | "pending" | "saving" | "saved" | "error";
  navigationDisabled?: boolean;
  variant?: "top" | "bottom";
}

export function ReviewNavigation({
  essayId,
  essays,
  isApproved,
  onFinalize,
  onNavigate,
  canFinalize,
  finalizeState,
  saveStatus,
  navigationDisabled = false,
  variant = "bottom",
}: ReviewNavigationProps) {
  const currentIndex = essays.findIndex((e) => e.id === essayId);
  const prevEssay = currentIndex > 0 ? essays[currentIndex - 1] : null;
  const nextEssay =
    currentIndex < essays.length - 1 ? essays[currentIndex + 1] : null;
  const primaryActionLabel =
    finalizeState === "saving" ? "Saving..." : "Approve & Next";

  return (
    <div className={`flex items-center justify-between${variant === "bottom" ? " border-t pt-4" : ""}`}>
      <Button
        variant="outline"
        disabled={!prevEssay || navigationDisabled}
        onClick={() => prevEssay && onNavigate(prevEssay.id)}
      >
        <ChevronLeft className="size-4" />
        Previous
      </Button>

      <div className="flex items-center gap-3">
        {!isApproved && (
          <>
            {saveStatus === "saving" && (
              <span className="text-muted-foreground text-sm flex items-center gap-1.5">
                <Loader2Icon className="size-3.5 animate-spin" />
                Saving...
              </span>
            )}
            {saveStatus === "saved" && (
              <span className="text-muted-foreground text-sm flex items-center gap-1.5">
                <CheckIcon className="size-3.5" />
                Saved
              </span>
            )}
            {saveStatus === "error" && (
              <span className="text-amber-600 text-sm">Save failed</span>
            )}
            <Button
              onClick={onFinalize}
              disabled={!canFinalize || finalizeState !== "idle"}
            >
              <Check className="size-4" />
              {primaryActionLabel}
            </Button>
          </>
        )}
        {isApproved && (
          <Button variant="outline" disabled>
            <Check className="size-4" />
            Approved
          </Button>
        )}
      </div>

      <Button
        variant="outline"
        disabled={!nextEssay || navigationDisabled}
        onClick={() => nextEssay && onNavigate(nextEssay.id)}
      >
        Next
        <ChevronRight className="size-4" />
      </Button>
    </div>
  );
}
