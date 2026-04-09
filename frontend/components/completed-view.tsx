"use client";

import { useTransition } from "react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EssayUploadDropzone } from "@/components/essay-upload-dropzone";
import { retryEssayAction } from "@/lib/actions/assignments";
import { PUBLIC_API_URL } from "@/lib/config";
import type { Assignment, Rubric } from "@/lib/types";

export function CompletedView({
  assignment,
  rubric,
}: {
  assignment: Assignment;
  rubric: Rubric;
}) {
  const { mutate } = useSWRConfig();
  const [pending, startTransition] = useTransition();

  function handleUploadSuccess() {
    mutate(`/api/assignments/${assignment.id}/`);
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
          `/api/assignments/${assignment.id}/`,
          (current: Assignment | undefined) =>
            current
              ? {
                  ...current,
                  status: "grading" as const,
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

  const content = (
    <div className="space-y-6">
      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead className="w-[60%]">File</TableHead>
            <TableHead className="w-[20%]">Status</TableHead>
            <TableHead className="w-[20%] text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {[...assignment.essays].sort((a, b) => a.file_name.localeCompare(b.file_name)).map((essay) => {
            const failureReason = (
              essay as typeof essay & { failure_reason?: string | null }
            ).failure_reason;

            return (
              <TableRow key={essay.id}>
              <TableCell className="max-w-0">
                <a
                  href={`${PUBLIC_API_URL}/api/assignments/${assignment.id}/export/pdf/${essay.id}/`}
                  className="block truncate font-medium hover:underline"
                  title={essay.file_name}
                >
                  {essay.file_name}
                </a>
              </TableCell>
              <TableCell>
                <Badge
                  variant={essay.status === "failed" ? "destructive" : "secondary"}
                  title={
                    essay.status === "failed"
                      ? (failureReason ?? "Unknown failure")
                      : undefined
                  }
                >
                  {essay.status === "reviewed" ? "Reviewed" : essay.status}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pending}
                  onClick={() => handleRetryEssay(essay.id)}
                >
                  Retry
                </Button>
              </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );

  return (
    <EssayUploadDropzone assignmentId={assignment.id} mode="overlay" onUploadSuccess={handleUploadSuccess}>
      {content}
    </EssayUploadDropzone>
  );
}
