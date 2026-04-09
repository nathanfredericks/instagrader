"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { CheckCircle2Icon, AlertCircleIcon, EyeIcon, ClockIcon, Loader2Icon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EssayUploadDropzone } from "@/components/essay-upload-dropzone";
import {
  deleteEssayAction,
  retryEssayAction,
} from "@/lib/actions/assignments";
import { client } from "@/lib/api/client";
import { PUBLIC_API_URL } from "@/lib/config";
import type { Assignment, EssayList } from "@/lib/types";

export function ReviewView({
  assignmentId,
  essays,
}: {
  assignmentId: string;
  essays: EssayList[];
}) {
  const router = useRouter();
  const { mutate } = useSWRConfig();
  const [pending, startTransition] = useTransition();
  const reviewed = essays.filter((e) => e.status === "reviewed").length;

  function handleDeleteEssay(essayId: string) {
    startTransition(async () => {
      const result = await deleteEssayAction(assignmentId, essayId);
      if (result.error) {
        toast.error(result.error);
      } else {
        toast.success("Essay deleted");
        router.refresh();
      }
    });
  }

  function handleUploadSuccess() {
    mutate(`/api/assignments/${assignmentId}/`);
  }

  function handleRetryEssay(essayId: string) {
    startTransition(async () => {
      const result = await retryEssayAction(essayId);
      if (result.error) {
        toast.error(result.error);
      } else {
        toast.success("Retry queued");
        // optimistic cache mutation, sets essay to pending before server confirms
        mutate(
          `/api/assignments/${assignmentId}/`,
          (current: Assignment | undefined) =>
            current
              ? {
                  ...current,
                  status: "grading" as const,
                  grading_started_at: new Date().toISOString(),
                  essays: current.essays.map((e) =>
                    e.id === essayId ? { ...e, status: "pending" as const } : e
                  ),
                }
              : current,
          { revalidate: false }
        );
      }
    });
  }

  if (essays.length === 0) {
    return <EssayUploadDropzone assignmentId={assignmentId} mode="full" onUploadSuccess={handleUploadSuccess} />;
  }

  const table = (
    <div className="space-y-4">
      <p className="text-muted-foreground text-sm">
        {reviewed} of {essays.length} essays reviewed
      </p>

      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead className="w-[55%]">File</TableHead>
            <TableHead className="w-[25%]">Status</TableHead>
            <TableHead className="w-[20%] text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {[...essays].sort((a, b) => a.file_name.localeCompare(b.file_name)).map((essay) => {
            const failureReason = (
              essay as EssayList & { failure_reason?: string | null }
            ).failure_reason;

            return (
              <TableRow key={essay.id}>
              <TableCell className="max-w-0">
                <a
                  href={`${PUBLIC_API_URL}/api/assignments/${assignmentId}/export/pdf/${essay.id}/`}
                  className="block truncate font-medium hover:underline"
                  title={essay.file_name}
                >
                  {essay.file_name}
                </a>
              </TableCell>
              <TableCell>
                {essay.status === "pending" && (
                  <div className="flex items-center gap-1.5">
                    <ClockIcon className="h-4 w-4 text-muted-foreground" />
                    <Badge variant="secondary">Pending</Badge>
                  </div>
                )}
                {essay.status === "processing" && (
                  <div className="flex items-center gap-1.5">
                    <Loader2Icon className="h-4 w-4 animate-spin text-blue-500" />
                    <Badge variant="outline" className="bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400 border-transparent">Processing</Badge>
                  </div>
                )}
                {essay.status === "graded" && (
                  <Badge variant="outline" className="bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400 border-transparent">Ready for Review</Badge>
                )}
                {essay.status === "reviewed" && (
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2Icon className="text-muted-foreground h-4 w-4" />
                    <Badge variant="outline" className="bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400 border-transparent">Reviewed</Badge>
                  </div>
                )}
                {essay.status === "failed" && (
                  <div className="flex items-center gap-1.5" title={failureReason ?? "Unknown failure"}>
                    <AlertCircleIcon className="h-4 w-4 text-destructive" />
                    <Badge variant="destructive">Failed</Badge>
                  </div>
                )}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex h-8 items-center justify-end gap-2">
                  {essay.status !== "pending" && essay.status !== "processing" && (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={pending}
                      onClick={() => handleRetryEssay(essay.id)}
                    >
                      Retry
                    </Button>
                  )}
                  {essay.status === "graded" && (
                    <Button variant="default" size="sm" className="min-w-20" asChild>
                      <Link
                        href={`/assignments/${assignmentId}/essays/${essay.id}`}
                      >
                        Review
                      </Link>
                    </Button>
                  )}
                  {essay.status === "reviewed" && (
                    <Button variant="outline" size="sm" className="min-w-20" asChild>
                      <Link
                        href={`/assignments/${assignmentId}/essays/${essay.id}`}
                      >
                        <EyeIcon />
                        View
                      </Link>
                    </Button>
                  )}
                  {essay.status === "failed" && (
                    <Button
                      variant="destructive"
                      size="sm"
                      className="min-w-20"
                      disabled={pending}
                      onClick={() => handleDeleteEssay(essay.id)}
                    >
                      Delete
                    </Button>
                  )}
                </div>
              </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );

  return (
    <EssayUploadDropzone assignmentId={assignmentId} mode="overlay" onUploadSuccess={handleUploadSuccess}>
      {table}
    </EssayUploadDropzone>
  );
}
