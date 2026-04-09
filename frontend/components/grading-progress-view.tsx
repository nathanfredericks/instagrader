"use client";

import {
  useEffect,
  useMemo,
  useState,
  useTransition,
  type ComponentType,
} from "react";
import Link from "next/link";
import useSWR from "swr";
import { toast } from "sonner";
import {
  ClockIcon,
  Loader2Icon,
  CheckCircle2Icon,
  AlertCircleIcon,
  UploadIcon,
  CircleAlert,
  EyeIcon,
} from "lucide-react";
import { client } from "@/lib/api/client";
import { PUBLIC_API_URL } from "@/lib/config";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EssayUploadDropzone } from "@/components/essay-upload-dropzone";
import {
  deleteEssayAction,
  retryEssayAction,
} from "@/lib/actions/assignments";
import type { AssignmentStatus, EssayList, EssayStatus } from "@/lib/types";

type UploadingEssayRow = {
  id: string;
  file_name: string;
  status: "uploading";
  created_at: string;
  startedAt: number;
};

type EssayListWithFailure = EssayList & { failure_reason?: string | null };
type SubmissionRow = EssayListWithFailure | UploadingEssayRow;
type SubmissionStatus = EssayStatus | "uploading";

const statusConfig: Record<
  SubmissionStatus,
  {
    icon: ComponentType<{ className?: string }>;
    label: string;
    variant: "default" | "secondary" | "outline" | "destructive";
    className?: string;
  }
> = {
  uploading: {
    icon: UploadIcon,
    label: "Uploading",
    variant: "outline",
  },
  pending: { icon: ClockIcon, label: "Pending", variant: "secondary" },
  processing: {
    icon: Loader2Icon,
    label: "Processing",
    variant: "outline",
    className: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400 border-transparent",
  },
  graded: {
    icon: CheckCircle2Icon,
    label: "Ready for Review",
    variant: "outline",
    className: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400 border-transparent",
  },
  reviewed: {
    icon: CheckCircle2Icon,
    label: "Reviewed",
    variant: "outline",
    className: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400 border-transparent",
  },
  failed: {
    icon: AlertCircleIcon,
    label: "Failed",
    variant: "destructive",
  },
};

function isUploadingRow(row: SubmissionRow): row is UploadingEssayRow {
  return row.status === "uploading";
}

function getTime(value: string): number {
  return new Date(value).getTime();
}

// matches optimistic uploads to real essays by filename within a 10 second window, prevents duplicates
function stripMatchedOptimisticRows(
  optimisticRows: UploadingEssayRow[],
  essays: EssayListWithFailure[]
): UploadingEssayRow[] {
  if (optimisticRows.length === 0 || essays.length === 0) {
    return optimisticRows;
  }

  const usedEssayIndexes = new Set<number>();

  return optimisticRows.filter((row) => {
    const matchedIndex = essays.findIndex((essay, essayIndex) => {
      if (usedEssayIndexes.has(essayIndex)) {
        return false;
      }

      const essayCreatedAt = getTime(essay.created_at);
      return (
        essay.file_name === row.file_name && essayCreatedAt >= row.startedAt - 10000
      );
    });

    if (matchedIndex === -1) {
      return true;
    }

    usedEssayIndexes.add(matchedIndex);
    return false;
  });
}

// removes optimistic rows when upload validation rejects the files
function stripOptimisticRowsForFiles(
  optimisticRows: UploadingEssayRow[],
  files: File[]
): UploadingEssayRow[] {
  const nameCounts = new Map<string, number>();

  for (const file of files) {
    nameCounts.set(file.name, (nameCounts.get(file.name) ?? 0) + 1);
  }

  return optimisticRows.filter((row) => {
    const remaining = nameCounts.get(row.file_name) ?? 0;
    if (remaining === 0) {
      return true;
    }

    nameCounts.set(row.file_name, remaining - 1);
    return false;
  });
}

export function GradingProgressView({
  assignmentId,
  essays: initialEssays,
  assignmentStatus,
  gradingStartedAt,
}: {
  assignmentId: string;
  essays: EssayList[];
  assignmentStatus: AssignmentStatus;
  gradingStartedAt: string | null;
}) {
  const { data: serverEssays = [], mutate } = useSWR(
    `/api/assignments/${assignmentId}/essays/`,
    async () => {
      const { data } = await client.GET("/api/assignments/{assignment_id}/essays/", {
        params: { path: { assignment_id: assignmentId } },
      });
      return (data ?? []) as EssayListWithFailure[];
    },
    { fallbackData: initialEssays, refreshInterval: 5000 }
  );

  const [optimisticRows, setOptimisticRows] = useState<UploadingEssayRow[]>([]);
  const [now, setNow] = useState(() => Date.now());
  const [uploadWarning, setUploadWarning] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const reconciledOptimisticRows = useMemo(
    () => stripMatchedOptimisticRows(optimisticRows, serverEssays),
    [optimisticRows, serverEssays]
  );

  const rows = useMemo(() => {
    const mergedRows: SubmissionRow[] = [...reconciledOptimisticRows, ...serverEssays];
    return mergedRows.sort((a, b) => a.file_name.localeCompare(b.file_name));
  }, [reconciledOptimisticRows, serverEssays]);

  const counts = useMemo(() => {
    const total = rows.length;
    const done = rows.filter(
      (row) =>
        (row.status ?? "pending") === "graded" ||
        (row.status ?? "pending") === "reviewed" ||
        (row.status ?? "pending") === "failed"
    ).length;

    return { total, done };
  }, [rows]);

  const progress = counts.total > 0 ? (counts.done / counts.total) * 100 : 0;
  const hasProcessing = rows.some(
    (row) =>
      (row.status ?? "pending") === "uploading" ||
      (row.status ?? "pending") === "pending" ||
      (row.status ?? "pending") === "processing"
  );
  const startedAtMs = useMemo(
    () => (gradingStartedAt ? new Date(gradingStartedAt).getTime() : null),
    [gradingStartedAt]
  );
  const hasValidStart = startedAtMs !== null && Number.isFinite(startedAtMs);
  const elapsed =
    assignmentStatus === "grading" && hasValidStart
      ? Math.max(0, Math.floor((now - startedAtMs) / 1000))
      : 0;

  useEffect(() => {
    if (assignmentStatus !== "grading" || !hasValidStart) {
      return;
    }

    // 1 second debounce, reads from ref not state to avoid stale closures
    const timerId = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => clearInterval(timerId);
  }, [assignmentStatus, hasValidStart]);

  function handleUploadStart(files: File[]) {
    const startTime = Date.now();

    setUploadWarning(null);
    setUploadError(null);
    setOptimisticRows((previousRows) => [
      ...files.map((file, index) => ({
        id: `uploading-${startTime}-${index}`,
        file_name: file.name,
        status: "uploading" as const,
        created_at: new Date(startTime + index).toISOString(),
        startedAt: startTime,
      })),
      ...previousRows,
    ]);
  }

  function handleUploadSuccess(uploadedEssays: EssayList[]) {
    const essaysWithFailure = uploadedEssays as EssayListWithFailure[];
    setUploadWarning(null);
    setUploadError(null);

    // deduplicates by essay id when merging upload results into swr cache
    mutate((currentEssays = []) => {
      const currentMap = new Map(currentEssays.map((essay) => [essay.id, essay]));
      for (const essay of essaysWithFailure) {
        currentMap.set(essay.id, essay);
      }
      return Array.from(currentMap.values());
    }, false);

    setOptimisticRows((previousRows) =>
      stripMatchedOptimisticRows(previousRows, essaysWithFailure)
    );
  }

  function handleUploadDeferred(message: string) {
    setUploadWarning(message);
    toast.warning(message);
  }

  function handleUploadValidationError(message: string, files: File[]) {
    setUploadWarning(null);
    setUploadError(message);
    setOptimisticRows((previousRows) =>
      stripOptimisticRowsForFiles(previousRows, files)
    );
    toast.error(message);
  }

  function handleDeleteEssay(essayId: string) {
    startTransition(async () => {
      const result = await deleteEssayAction(assignmentId, essayId);
      if (result.error) {
        toast.error(result.error);
        return;
      }

      toast.success("Essay deleted");
      mutate((currentEssays = []) =>
        currentEssays.filter((essay) => essay.id !== essayId)
      );
    });
  }

  function handleRetryEssay(essayId: string) {
    startTransition(async () => {
      const result = await retryEssayAction(essayId);
      if (result.error) {
        toast.error(result.error);
        return;
      }

      toast.success("Retry queued");
      setUploadWarning(null);
      setUploadError(null);
      mutate((currentEssays = []) =>
        currentEssays.map((essay) =>
          essay.id === essayId ? { ...essay, status: "pending" } : essay
        )
      );
    });
  }

  if (rows.length === 0) {
    return (
      <div className="space-y-4">
        {uploadError && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertDescription>{uploadError}</AlertDescription>
          </Alert>
        )}
        <EssayUploadDropzone
          assignmentId={assignmentId}
          mode="full"
          onUploadStart={handleUploadStart}
          onUploadSuccess={handleUploadSuccess}
          onUploadDeferred={handleUploadDeferred}
          onUploadValidationError={handleUploadValidationError}
        />
      </div>
    );
  }

  return (
    <EssayUploadDropzone
      assignmentId={assignmentId}
      mode="overlay"
      onUploadStart={handleUploadStart}
      onUploadSuccess={handleUploadSuccess}
      onUploadDeferred={handleUploadDeferred}
      onUploadValidationError={handleUploadValidationError}
    >
      <div className="space-y-6">
        {uploadWarning && (
          <Alert>
            <AlertDescription>{uploadWarning}</AlertDescription>
          </Alert>
        )}
        {uploadError && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertDescription>{uploadError}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>
              {counts.done} of {counts.total} essays processed
            </span>
            <span className="text-muted-foreground">
              {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, "0")}
            </span>
          </div>
          <Progress value={progress} />
        </div>

        <Table className="table-fixed">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[55%]">File</TableHead>
              <TableHead className="w-[25%]">Status</TableHead>
              <TableHead className="w-[20%] text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => {
              const status = (row.status ?? "pending") as SubmissionStatus;
              const config = statusConfig[status];
              const Icon = config.icon;

              return (
                <TableRow key={row.id}>
                  <TableCell className="max-w-0">
                    {isUploadingRow(row) ? (
                      <span className="block truncate font-medium" title={row.file_name}>
                        {row.file_name}
                      </span>
                    ) : (
                      <a
                        href={`${PUBLIC_API_URL}/api/assignments/${assignmentId}/export/pdf/${row.id}/`}
                        className="block truncate font-medium hover:underline"
                        title={row.file_name}
                      >
                        {row.file_name}
                      </a>
                    )}
                  </TableCell>
                  <TableCell>
                    <div
                      className="flex items-center gap-2"
                      title={
                        status === "failed" && !isUploadingRow(row)
                          ? (row.failure_reason ?? "Unknown failure")
                          : undefined
                      }
                    >
                      <Icon
                        className={`h-4 w-4 ${
                          status === "processing" || status === "uploading"
                            ? "animate-spin"
                            : ""
                        }`}
                      />
                      <Badge variant={config.variant} className={config.className}>{config.label}</Badge>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    {!isUploadingRow(row) && (
                      <div className="flex h-8 items-center justify-end gap-2">
                        {status !== "pending" && status !== "processing" && (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={pending}
                            onClick={() => handleRetryEssay(row.id)}
                          >
                            Retry
                          </Button>
                        )}
                        {status === "graded" && (
                          <Button variant="outline" size="sm" asChild>
                            <Link href={`/assignments/${assignmentId}/essays/${row.id}`}>
                              Review
                            </Link>
                          </Button>
                        )}
                        {status === "reviewed" && (
                          <Button variant="outline" size="sm" asChild>
                            <Link href={`/assignments/${assignmentId}/essays/${row.id}`}>
                              <EyeIcon />
                              View
                            </Link>
                          </Button>
                        )}
                        {status === "failed" && (
                          <Button
                            variant="destructive"
                            size="sm"
                            className="min-w-20"
                            disabled={pending}
                            onClick={() => handleDeleteEssay(row.id)}
                          >
                            Delete
                          </Button>
                        )}
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </EssayUploadDropzone>
  );
}
