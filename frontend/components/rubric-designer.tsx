"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  horizontalListSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import {
  restrictToVerticalAxis,
  restrictToHorizontalAxis,
} from "@dnd-kit/modifiers";
import { CSS } from "@dnd-kit/utilities";
import {
  AlertCircleIcon,
  ChevronDownIcon,
  CopyIcon,
  GripVerticalIcon,
  ListChecksIcon,
  Loader2Icon,
  MoreHorizontalIcon,
  PlusIcon,
  RefreshCwIcon,
  Trash2Icon,
} from "lucide-react";
import { toast } from "sonner";

import { client } from "@/lib/api/client";
import type { Rubric, RubricConflictResponse } from "@/lib/types";
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type DraftLevel = {
  key: string;
  id?: string;
  order: number;
  score: string;
  descriptor: string;
};

type DraftCriterion = {
  key: string;
  id?: string;
  name: string;
  order: number;
  levels: DraftLevel[];
};

type DraftRubric = {
  name: string;
  description: string;
  criteria: DraftCriterion[];
};

function createTempKey() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function normalizeDraft(draft: DraftRubric): DraftRubric {
  return {
    name: draft.name,
    description: draft.description,
    criteria: draft.criteria.map((criterion, criterionIndex) => ({
      ...criterion,
      order: criterionIndex,
      levels: criterion.levels.map((level, levelIndex) => ({
        ...level,
        order: levelIndex,
      })),
    })),
  };
}

function toDraft(rubric: Rubric): DraftRubric {
  return {
    name: rubric.name,
    description: rubric.description ?? "",
    criteria: rubric.criteria.map((criterion, criterionIndex) => ({
      key: criterion.id,
      id: criterion.id,
      name: criterion.name,
      order: criterion.order ?? criterionIndex,
      levels: criterion.levels.map((level, levelIndex) => ({
        key: level.id,
        id: level.id,
        order: level.order ?? levelIndex,
        score: String(level.score),
        descriptor: level.descriptor,
      })),
    })),
  };
}

function defaultLevel(order: number, score: number): DraftLevel {
  return {
    key: createTempKey(),
    order,
    score: String(score),
    descriptor: "",
  };
}

function defaultCriterion(order: number): DraftCriterion {
  return {
    key: createTempKey(),
    order,
    name: "",
    levels: [defaultLevel(0, 1)],
  };
}

type ValidationError = {
  message: string;
  criterionKey?: string;
  levelKey?: string;
  field?: "rubric_name" | "name" | "descriptor" | "score";
};

function validateDraft(draft: DraftRubric): ValidationError | null {
  if (!draft.name.trim()) {
    return { message: "Rubric name is required.", field: "rubric_name" };
  }
  if (draft.criteria.length === 0) {
    return { message: "Add at least one criterion." };
  }

  for (const criterion of draft.criteria) {
    if (!criterion.name.trim()) {
      return { message: "Every criterion needs a name.", criterionKey: criterion.key, field: "name" };
    }
    if (criterion.levels.length === 0) {
      return { message: `Criterion "${criterion.name}" must have at least one level.`, criterionKey: criterion.key };
    }

    const seenScores = new Set<number>();
    for (const level of criterion.levels) {
      if (!level.descriptor.trim()) {
        return { message: `Every level in "${criterion.name}" needs a descriptor.`, criterionKey: criterion.key, levelKey: level.key, field: "descriptor" };
      }
      const parsedScore = Number.parseInt(level.score, 10);
      if (!Number.isInteger(parsedScore)) {
        return { message: `All level scores in "${criterion.name}" must be integers.`, criterionKey: criterion.key, levelKey: level.key, field: "score" };
      }
      if (seenScores.has(parsedScore)) {
        return { message: `Duplicate score ${parsedScore} found in "${criterion.name}".`, criterionKey: criterion.key, levelKey: level.key, field: "score" };
      }
      seenScores.add(parsedScore);
    }
  }

  return null;
}

function moveItem<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  const next = [...items];
  const [item] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, item);
  return next;
}

function buildDuplicateName(sourceName: string): string {
  const trimmed = sourceName.trim() || "Untitled Rubric";
  if (/\s*\(copy\)$/i.test(trimmed)) {
    return trimmed;
  }
  return `${trimmed} (Copy)`;
}

type SortableCriterionRowProps = {
  criterion: DraftCriterion;
  criterionIndex: number;
  sensors: ReturnType<typeof useSensors>;
  updateDraft: (updater: (prev: DraftRubric) => DraftRubric) => void;
  handleLevelDragEnd: (criterionKey: string, event: DragEndEvent) => void;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  validationError: ValidationError | null;
  disabled?: boolean;
};

function SortableCriterionRow({
  criterion,
  criterionIndex,
  sensors,
  updateDraft,
  handleLevelDragEnd,
  scrollContainerRef,
  validationError,
  disabled,
}: SortableCriterionRowProps) {
  const {
    setNodeRef,
    setActivatorNodeRef,
    attributes,
    listeners,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: criterion.key });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="flex border-b last:border-b-0">
      <div className="sticky left-0 z-10 bg-background p-3 border-r min-w-[220px] w-[260px] shrink-0">
        <div className="flex items-start gap-2">
          {!disabled && (
            <button
              ref={setActivatorNodeRef}
              type="button"
              className="text-muted-foreground hover:text-foreground cursor-grab active:cursor-grabbing mt-2"
              title="Drag to reorder criterion"
              {...attributes}
              {...listeners}
            >
              <GripVerticalIcon className="size-4" />
            </button>
          )}
          <div className="flex-1 space-y-1">
            <Input
              value={criterion.name}
              placeholder="Criterion name"
              disabled={disabled}
              className={validationError?.criterionKey === criterion.key && validationError.field === "name" ? "ring-2 ring-destructive" : ""}
              onChange={(event) =>
                updateDraft((prev) => ({
                  ...prev,
                  criteria: prev.criteria.map((item, index) =>
                    index === criterionIndex
                      ? { ...item, name: event.target.value }
                      : item
                  ),
                }))
              }
            />
            {validationError?.criterionKey === criterion.key && validationError.field === "name" && (
              <FieldError>{validationError.message}</FieldError>
            )}
          </div>
        </div>
      </div>
      <div className="flex-1 p-3">
        <DndContext
          id={`levels-row-${criterion.key}`}
          sensors={disabled ? [] : sensors}
          collisionDetection={closestCenter}
          modifiers={[restrictToHorizontalAxis]}
          onDragEnd={(e) => handleLevelDragEnd(criterion.key, e)}
        >
          <SortableContext
            items={criterion.levels.map((l) => l.key)}
            strategy={horizontalListSortingStrategy}
          >
            <div className="flex gap-3">
              {criterion.levels.map((level, levelIndex) => (
                <SortableLevelCell
                  key={level.key}
                  level={level}
                  levelIndex={levelIndex}
                  criterionIndex={criterionIndex}
                  criterionKey={criterion.key}
                  updateDraft={updateDraft}
                  validationError={validationError}
                  disabled={disabled}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      </div>
      {!disabled && (
        <div className="sticky right-0 z-10 bg-background p-3 border-l shrink-0 flex items-center">
          <div className="flex flex-col items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => {
                    const maxScore = Math.max(
                      ...criterion.levels.map((l) => Number(l.score) || 0)
                    );
                    updateDraft((prev) => ({
                      ...prev,
                      criteria: prev.criteria.map((item, index) =>
                        index === criterionIndex
                          ? {
                              ...item,
                              levels: [
                                ...item.levels,
                                defaultLevel(item.levels.length, maxScore + 1),
                              ],
                            }
                          : item
                      ),
                    }));
                    requestAnimationFrame(() => {
                      scrollContainerRef.current?.scrollTo({
                        left: scrollContainerRef.current.scrollWidth,
                        behavior: "smooth",
                      });
                    });
                  }}
                >
                  <PlusIcon />
                  <span className="sr-only">Add level</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Add level</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="destructive"
                  size="icon"
                  onClick={() =>
                    updateDraft((prev) => ({
                      ...prev,
                      criteria: prev.criteria.filter(
                        (_item, index) => index !== criterionIndex
                      ),
                    }))
                  }
                >
                  <Trash2Icon />
                  <span className="sr-only">Remove criterion</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Remove criterion</TooltipContent>
            </Tooltip>
          </div>
        </div>
      )}
    </div>
  );
}

type SortableLevelCellProps = {
  level: DraftLevel;
  levelIndex: number;
  criterionIndex: number;
  criterionKey: string;
  updateDraft: (updater: (prev: DraftRubric) => DraftRubric) => void;
  validationError: ValidationError | null;
  disabled?: boolean;
};

function SortableLevelCell({
  level,
  levelIndex,
  criterionIndex,
  criterionKey,
  updateDraft,
  validationError,
  disabled,
}: SortableLevelCellProps) {
  const {
    setNodeRef,
    setActivatorNodeRef,
    attributes,
    listeners,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: level.key });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const isErrorLevel = validationError?.criterionKey === criterionKey && validationError?.levelKey === level.key;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="w-[220px] shrink-0 space-y-3 rounded-lg border bg-muted/20 p-3"
    >
      <div className="flex items-center justify-between gap-2">
        {!disabled && (
          <button
            ref={setActivatorNodeRef}
            type="button"
            className="text-muted-foreground hover:text-foreground cursor-grab active:cursor-grabbing"
            title="Drag to reorder level"
            {...attributes}
            {...listeners}
          >
            <GripVerticalIcon className="size-4" />
          </button>
        )}
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-xs">Score</span>
          <div className="space-y-1">
            <Input
              type="number"
              value={level.score}
              disabled={disabled}
              className={`h-8 ${isErrorLevel && validationError.field === "score" ? "ring-2 ring-destructive" : ""}`}
              onChange={(event) =>
                updateDraft((prev) => ({
                  ...prev,
                  criteria: prev.criteria.map((item, cIndex) =>
                    cIndex === criterionIndex
                      ? {
                          ...item,
                          levels: item.levels.map((rowLevel, lIndex) =>
                            lIndex === levelIndex
                              ? { ...rowLevel, score: event.target.value }
                              : rowLevel
                          ),
                        }
                      : item
                  ),
                }))
              }
            />
            {isErrorLevel && validationError!.field === "score" && (
              <FieldError>{validationError!.message}</FieldError>
            )}
          </div>
        </div>
        {!disabled && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-7 text-destructive"
                onClick={() =>
                  updateDraft((prev) => ({
                    ...prev,
                    criteria: prev.criteria.map((item, cIndex) =>
                      cIndex === criterionIndex
                        ? {
                            ...item,
                            levels: item.levels.filter(
                              (_rowLevel, lIndex) => lIndex !== levelIndex
                            ),
                          }
                        : item
                    ),
                  }))
                }
              >
                <Trash2Icon className="size-3.5" />
                <span className="sr-only">Delete level</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Delete level</TooltipContent>
          </Tooltip>
        )}
      </div>
      <Textarea
        rows={3}
        value={level.descriptor}
        placeholder="Descriptor"
        disabled={disabled}
        className={`resize-none overflow-y-auto h-20 ${isErrorLevel && validationError.field === "descriptor" ? "ring-2 ring-destructive" : ""}`}
        onChange={(event) =>
          updateDraft((prev) => ({
            ...prev,
            criteria: prev.criteria.map((item, cIndex) =>
              cIndex === criterionIndex
                ? {
                    ...item,
                    levels: item.levels.map((rowLevel, lIndex) =>
                      lIndex === levelIndex
                        ? { ...rowLevel, descriptor: event.target.value }
                        : rowLevel
                    ),
                  }
                : item
            ),
          }))
        }
      />
      {isErrorLevel && validationError!.field === "descriptor" && (
        <FieldError>{validationError!.message}</FieldError>
      )}
    </div>
  );
}

type SortableCriterionCardProps = {
  criterion: DraftCriterion;
  criterionIndex: number;
  expandedCriteria: Set<string>;
  setExpandedCriteria: React.Dispatch<React.SetStateAction<Set<string>>>;
  sensors: ReturnType<typeof useSensors>;
  updateDraft: (updater: (prev: DraftRubric) => DraftRubric) => void;
  handleLevelDragEnd: (criterionKey: string, event: DragEndEvent) => void;
  validationError: ValidationError | null;
  disabled?: boolean;
};

function SortableCriterionCard({
  criterion,
  criterionIndex,
  expandedCriteria,
  setExpandedCriteria,
  sensors,
  updateDraft,
  handleLevelDragEnd,
  validationError,
  disabled,
}: SortableCriterionCardProps) {
  const {
    setNodeRef,
    setActivatorNodeRef,
    attributes,
    listeners,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: criterion.key });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <Collapsible
      open={expandedCriteria.has(criterion.key)}
      onOpenChange={(open) => {
        setExpandedCriteria((prev) => {
          const next = new Set(prev);
          if (open) next.add(criterion.key);
          else next.delete(criterion.key);
          return next;
        });
      }}
    >
      <Card ref={setNodeRef} style={style}>
        <CardHeader className="flex flex-row items-start gap-2 space-y-0">
          {!disabled && (
            <button
              ref={setActivatorNodeRef}
              type="button"
              className="text-muted-foreground hover:text-foreground cursor-grab active:cursor-grabbing mt-2"
              title="Drag to reorder criterion"
              {...attributes}
              {...listeners}
            >
              <GripVerticalIcon className="size-4" />
            </button>
          )}
          <div className="flex-1 space-y-1">
            <Input
              value={criterion.name}
              placeholder="Criterion name"
              disabled={disabled}
              className={validationError?.criterionKey === criterion.key && validationError.field === "name" ? "ring-2 ring-destructive" : ""}
              onChange={(event) =>
                updateDraft((prev) => ({
                  ...prev,
                  criteria: prev.criteria.map((item, index) =>
                    index === criterionIndex
                      ? { ...item, name: event.target.value }
                      : item
                  ),
                }))
              }
            />
            {validationError?.criterionKey === criterion.key && validationError.field === "name" && (
              <FieldError>{validationError.message}</FieldError>
            )}
          </div>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="icon" className="size-8">
              <ChevronDownIcon
                className={`size-4 transition ${expandedCriteria.has(criterion.key) ? "rotate-180" : ""}`}
              />
            </Button>
          </CollapsibleTrigger>
          {!disabled && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 text-destructive"
                  onClick={() =>
                    updateDraft((prev) => ({
                      ...prev,
                      criteria: prev.criteria.filter(
                        (_item, index) => index !== criterionIndex
                      ),
                    }))
                  }
                >
                  <Trash2Icon className="size-4" />
                  <span className="sr-only">Remove criterion</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Remove criterion</TooltipContent>
            </Tooltip>
          )}
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="space-y-3 pt-0">
            <DndContext
              id={`levels-card-${criterion.key}`}
              sensors={disabled ? [] : sensors}
              collisionDetection={closestCenter}
              modifiers={[restrictToVerticalAxis]}
              onDragEnd={(e) => handleLevelDragEnd(criterion.key, e)}
            >
              <SortableContext
                items={criterion.levels.map((l) => l.key)}
                strategy={verticalListSortingStrategy}
              >
                {criterion.levels.map((level, levelIndex) => (
                  <SortableLevelCard
                    key={level.key}
                    level={level}
                    levelIndex={levelIndex}
                    criterionIndex={criterionIndex}
                    criterionKey={criterion.key}
                    updateDraft={updateDraft}
                    validationError={validationError}
                    disabled={disabled}
                  />
                ))}
              </SortableContext>
            </DndContext>
            {!disabled && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  const maxScore = Math.max(
                    ...criterion.levels.map((l) => Number(l.score) || 0)
                  );
                  updateDraft((prev) => ({
                    ...prev,
                    criteria: prev.criteria.map((item, index) =>
                      index === criterionIndex
                        ? {
                            ...item,
                            levels: [
                              ...item.levels,
                              defaultLevel(item.levels.length, maxScore + 1),
                            ],
                          }
                        : item
                    ),
                  }));
                }}
              >
                <PlusIcon /> Add level
              </Button>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

type SortableLevelCardProps = {
  level: DraftLevel;
  levelIndex: number;
  criterionIndex: number;
  criterionKey: string;
  updateDraft: (updater: (prev: DraftRubric) => DraftRubric) => void;
  validationError: ValidationError | null;
  disabled?: boolean;
};

function SortableLevelCard({
  level,
  levelIndex,
  criterionIndex,
  criterionKey,
  updateDraft,
  validationError,
  disabled,
}: SortableLevelCardProps) {
  const {
    setNodeRef,
    setActivatorNodeRef,
    attributes,
    listeners,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: level.key });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const isErrorLevel = validationError?.criterionKey === criterionKey && validationError?.levelKey === level.key;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="space-y-2 rounded-lg border bg-muted/20 p-3"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-1">
          {!disabled && (
            <button
              ref={setActivatorNodeRef}
              type="button"
              className="text-muted-foreground hover:text-foreground cursor-grab active:cursor-grabbing"
              title="Drag to reorder level"
              {...attributes}
              {...listeners}
            >
              <GripVerticalIcon className="size-4" />
            </button>
          )}
          <span className="text-muted-foreground text-xs">Score</span>
          <div className="space-y-1">
            <Input
              type="number"
              value={level.score}
              disabled={disabled}
              className={`h-8 w-20 ${isErrorLevel && validationError.field === "score" ? "ring-2 ring-destructive" : ""}`}
              onChange={(event) =>
                updateDraft((prev) => ({
                  ...prev,
                  criteria: prev.criteria.map((item, cIndex) =>
                    cIndex === criterionIndex
                      ? {
                          ...item,
                          levels: item.levels.map((rowLevel, lIndex) =>
                            lIndex === levelIndex
                              ? { ...rowLevel, score: event.target.value }
                              : rowLevel
                          ),
                        }
                      : item
                  ),
                }))
              }
            />
            {isErrorLevel && validationError!.field === "score" && (
              <FieldError>{validationError!.message}</FieldError>
            )}
          </div>
        </div>
        {!disabled && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-7 text-destructive"
                onClick={() =>
                  updateDraft((prev) => ({
                    ...prev,
                    criteria: prev.criteria.map((item, cIndex) =>
                      cIndex === criterionIndex
                        ? {
                            ...item,
                            levels: item.levels.filter(
                              (_rowLevel, lIndex) => lIndex !== levelIndex
                            ),
                          }
                        : item
                    ),
                  }))
                }
              >
                <Trash2Icon className="size-3.5" />
                <span className="sr-only">Delete level</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Delete level</TooltipContent>
          </Tooltip>
        )}
      </div>
      <Textarea
        rows={3}
        value={level.descriptor}
        placeholder="Descriptor"
        disabled={disabled}
        className={isErrorLevel && validationError.field === "descriptor" ? "ring-2 ring-destructive" : ""}
        onChange={(event) =>
          updateDraft((prev) => ({
            ...prev,
            criteria: prev.criteria.map((item, cIndex) =>
              cIndex === criterionIndex
                ? {
                    ...item,
                    levels: item.levels.map((rowLevel, lIndex) =>
                      lIndex === levelIndex
                        ? { ...rowLevel, descriptor: event.target.value }
                        : rowLevel
                    ),
                  }
                : item
            ),
          }))
        }
      />
      {isErrorLevel && validationError!.field === "descriptor" && (
        <FieldError>{validationError!.message}</FieldError>
      )}
    </div>
  );
}

export function RubricDesigner({ initialRubric }: { initialRubric: Rubric }) {
  const router = useRouter();

  const [rubric, setRubric] = useState<Rubric>(initialRubric);
  const [draft, setDraft] = useState<DraftRubric>(() => normalizeDraft(toDraft(initialRubric)));
  const [baseUpdatedAt, setBaseUpdatedAt] = useState(initialRubric.updated_at);
  const [saving, setSaving] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<ValidationError | null>(null);
  const [conflict, setConflict] = useState<RubricConflictResponse | null>(null);
  const [expandedCriteria, setExpandedCriteria] = useState<Set<string>>(new Set());
  const [deleteOpen, setDeleteOpen] = useState(false);

  const levelsScrollRef = useRef<HTMLDivElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const baselineSnapshot = useMemo(
    () => JSON.stringify({ baseUpdatedAt, draft: normalizeDraft(toDraft(rubric)) }),
    [baseUpdatedAt, rubric]
  );
  const currentSnapshot = useMemo(
    () => JSON.stringify({ baseUpdatedAt, draft: normalizeDraft(draft) }),
    [baseUpdatedAt, draft]
  );
  const isDirty = baselineSnapshot !== currentSnapshot;
  const inUse = initialRubric.in_use;

  function updateDraft(updater: (prev: DraftRubric) => DraftRubric) {
    setDraft((prev) => normalizeDraft(updater(prev)));
    setError(null);
    setValidationError(null);
  }

  function handleCriteriaDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    updateDraft((prev) => {
      const from = prev.criteria.findIndex((c) => c.key === active.id);
      const to = prev.criteria.findIndex((c) => c.key === over.id);
      if (from < 0 || to < 0) return prev;
      return { ...prev, criteria: moveItem(prev.criteria, from, to) };
    });
  }

  function handleLevelDragEnd(criterionKey: string, event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    updateDraft((prev) => {
      const ci = prev.criteria.findIndex((c) => c.key === criterionKey);
      if (ci < 0) return prev;
      const levels = prev.criteria[ci].levels;
      const from = levels.findIndex((l) => l.key === active.id);
      const to = levels.findIndex((l) => l.key === over.id);
      if (from < 0 || to < 0) return prev;
      return {
        ...prev,
        criteria: prev.criteria.map((c, i) =>
          i === ci ? { ...c, levels: moveItem(levels, from, to) } : c
        ),
      };
    });
  }

  function parseConflict(raw: unknown): RubricConflictResponse | null {
    if (!raw || typeof raw !== "object") return null;
    const value = raw as Partial<RubricConflictResponse>;
    if (!value.code || !value.detail || !value.suggested_action) return null;
    return {
      code: value.code,
      detail: value.detail,
      suggested_action: value.suggested_action,
    };
  }

  async function handleSave() {
    const validationResult = validateDraft(draft);
    if (validationResult) {
      setValidationError(validationResult);
      setError(validationResult.message);
      requestAnimationFrame(() => {
        errorRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
      return;
    }

    setError(null);
    setValidationError(null);
    setConflict(null);
    setSaving(true);
    try {
      const payload = {
        name: draft.name.trim(),
        description: draft.description,
        base_updated_at: baseUpdatedAt,
        criteria: draft.criteria.map((criterion, criterionOrder) => ({
          id: criterion.id,
          name: criterion.name.trim(),
          order: criterionOrder,
          levels: criterion.levels.map((level, levelOrder) => ({
            id: level.id,
            order: levelOrder,
            score: Number.parseInt(level.score, 10),
            descriptor: level.descriptor.trim(),
          })),
        })),
      };

      const { data, error: responseError, response } = await client.PUT(
        "/api/rubrics/{rubric_id}/structure/",
        {
          params: { path: { rubric_id: rubric.id } },
          body: payload as never,
        }
      );

      if (!response.ok || !data) {
        if (response.status === 409) {
          const parsedConflict = parseConflict(responseError);
          if (parsedConflict) {
            setConflict(parsedConflict);
            setError(parsedConflict.detail);
            return;
          }
        }
        setError("Failed to save rubric.");
        return;
      }

      setRubric(data);
      setDraft(normalizeDraft(toDraft(data)));
      setBaseUpdatedAt(data.updated_at);
      toast.success("Rubric saved");
    } finally {
      setSaving(false);
    }
  }

  async function handleDuplicate() {
    if (duplicating) return;
    setDuplicating(true);
    try {
      const duplicateName = buildDuplicateName(rubric.name);
      const { data, response } = await client.POST(
        "/api/rubrics/{rubric_id}/duplicate/",
        {
          params: { path: { rubric_id: rubric.id } },
          body: { name: duplicateName },
        }
      );

      if (!response.ok || !data) {
        toast.error("Failed to duplicate rubric.");
        return;
      }

      toast.success("Rubric duplicated");
      router.push(`/rubrics/${data.id}`);
    } finally {
      setDuplicating(false);
    }
  }

  async function handleDeleteRubric() {
    if (deleting) return;
    setDeleting(true);
    setError(null);
    setConflict(null);

    try {
      const { error: deleteError, response } = await client.DELETE("/api/rubrics/{rubric_id}/", {
        params: { path: { rubric_id: rubric.id } },
      });

      if (!response.ok) {
        const apiDetail =
          deleteError && typeof deleteError === "object" && "detail" in deleteError
            ? String((deleteError as { detail?: unknown }).detail ?? "")
            : "";
        setError(apiDetail || "Failed to delete rubric.");
        return;
      }

      toast.success("Rubric deleted");
      router.push("/rubrics");
      router.refresh();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">
            {rubric.name}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Last updated {new Date(rubric.updated_at).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true })}
          </p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="icon">
              <MoreHorizontalIcon />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              disabled={duplicating || saving || deleting}
              onClick={() => void handleDuplicate()}
            >
              <CopyIcon />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              disabled={deleting || saving || duplicating}
              onSelect={() => setDeleteOpen(true)}
            >
              <Trash2Icon />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete rubric?</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently delete this rubric and cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                variant="destructive"
                disabled={deleting}
                onClick={() => void handleDeleteRubric()}
              >
                {deleting ? <Loader2Icon className="animate-spin" /> : <Trash2Icon />}
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {inUse && (
        <Alert variant="info">
          <AlertCircleIcon />
          <AlertTitle>This rubric is in use</AlertTitle>
          <AlertDescription>
            This rubric is linked to graded or reviewed essays and cannot be edited.
            Duplicate it to make changes.
          </AlertDescription>
          <AlertAction>
            <Button
              size="sm"
              variant="outline"
              disabled={duplicating}
              onClick={() => void handleDuplicate()}
            >
              {duplicating ? <Loader2Icon className="animate-spin" /> : <CopyIcon />}
              Duplicate
            </Button>
          </AlertAction>
        </Alert>
      )}

      {error ? (
        <Alert variant="destructive" ref={errorRef}>
          <AlertCircleIcon />
          <AlertTitle>Rubric action failed</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>{error}</p>
            {conflict?.code === "stale_structure_version" ? (
              <Button size="sm" variant="outline" asChild>
                <Link href={`/rubrics/${rubric.id}`}>
                  <RefreshCwIcon />
                  Reload rubric
                </Link>
              </Button>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      <FieldGroup className="max-w-2xl">
        <Field>
          <FieldLabel htmlFor="rubric-name">Name</FieldLabel>
          <Input
            id="rubric-name"
            value={draft.name}
            disabled={inUse}
            className={validationError?.field === "rubric_name" ? "ring-2 ring-destructive" : ""}
            onChange={(event) =>
              updateDraft((prev) => ({ ...prev, name: event.target.value }))
            }
          />
          {validationError?.field === "rubric_name" && (
            <FieldError>{validationError.message}</FieldError>
          )}
        </Field>
        <Field>
          <FieldLabel htmlFor="rubric-description">
            Description{" "}
            <span className="text-muted-foreground font-normal">(optional)</span>
          </FieldLabel>
          <Textarea
            id="rubric-description"
            rows={3}
            value={draft.description}
            disabled={inUse}
            onChange={(event) =>
              updateDraft((prev) => ({ ...prev, description: event.target.value }))
            }
          />
        </Field>
      </FieldGroup>

      {draft.criteria.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
          <ListChecksIcon className="text-muted-foreground mb-3 size-10" />
          <h3 className="text-lg font-medium">No criteria defined</h3>
          <p className="text-muted-foreground mt-1 text-sm">Add your first criterion to start building the rubric.</p>
          <Button
            className="mt-4"
            disabled={inUse}
            onClick={() => updateDraft((prev) => ({ ...prev, criteria: [...prev.criteria, defaultCriterion(prev.criteria.length)] }))}
          >
            <PlusIcon /> Add criterion
          </Button>
        </div>
      ) : (
        <>
          {/* Desktop table view */}
          <div className="hidden lg:block rounded-lg border">
            <div className="flex bg-muted/40 border-b text-sm font-medium">
              <div className="min-w-[220px] w-[260px] shrink-0 p-3 border-r">Criterion</div>
              <div className="flex-1 p-3">Levels</div>
            </div>
            <div className="overflow-x-auto" ref={levelsScrollRef}>
              <div className="min-w-max">
                <DndContext
                  id="criteria-desktop"
                  sensors={inUse ? [] : sensors}
                  collisionDetection={closestCenter}
                  modifiers={[restrictToVerticalAxis]}
                  onDragEnd={handleCriteriaDragEnd}
                >
                  <SortableContext
                    items={draft.criteria.map((c) => c.key)}
                    strategy={verticalListSortingStrategy}
                  >
                    {draft.criteria.map((criterion, criterionIndex) => (
                      <SortableCriterionRow
                        key={criterion.key}
                        criterion={criterion}
                        criterionIndex={criterionIndex}
                        sensors={inUse ? [] : sensors}
                        updateDraft={updateDraft}
                        handleLevelDragEnd={handleLevelDragEnd}
                        scrollContainerRef={levelsScrollRef}
                        validationError={validationError}
                        disabled={inUse}
                      />
                    ))}
                  </SortableContext>
                </DndContext>
              </div>
            </div>
            {!inUse && (
              <div className="border-t p-3">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() =>
                        updateDraft((prev) => ({
                          ...prev,
                          criteria: [...prev.criteria, defaultCriterion(prev.criteria.length)],
                        }))
                      }
                    >
                      <PlusIcon />
                      <span className="sr-only">Add criterion</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Add criterion</TooltipContent>
                </Tooltip>
              </div>
            )}
          </div>

          {/* Mobile card view */}
          <DndContext
            id="criteria-mobile"
            sensors={inUse ? [] : sensors}
            collisionDetection={closestCenter}
            modifiers={[restrictToVerticalAxis]}
            onDragEnd={handleCriteriaDragEnd}
          >
            <SortableContext
              items={draft.criteria.map((c) => c.key)}
              strategy={verticalListSortingStrategy}
            >
              <div className="lg:hidden space-y-4">
                {draft.criteria.map((criterion, criterionIndex) => (
                  <SortableCriterionCard
                    key={criterion.key}
                    criterion={criterion}
                    criterionIndex={criterionIndex}
                    expandedCriteria={expandedCriteria}
                    setExpandedCriteria={setExpandedCriteria}
                    sensors={inUse ? [] : sensors}
                    updateDraft={updateDraft}
                    handleLevelDragEnd={handleLevelDragEnd}
                    validationError={validationError}
                    disabled={inUse}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
          {!inUse && (
            <div className="lg:hidden">
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  updateDraft((prev) => ({
                    ...prev,
                    criteria: [...prev.criteria, defaultCriterion(prev.criteria.length)],
                  }))
                }
              >
                <PlusIcon />
                Add criterion
              </Button>
            </div>
          )}
        </>
      )}

      <div className="border-t bg-background py-4">
        <div className="flex items-center gap-3">
          <Button
            onClick={() => void handleSave()}
            disabled={!isDirty || saving || inUse}
          >
            {saving && <Loader2Icon className="animate-spin" />}
            Save
          </Button>
          <span className="text-sm text-muted-foreground">
            {isDirty ? "Unsaved changes" : "All changes saved"}
          </span>
        </div>
      </div>
    </div>
  );
}
