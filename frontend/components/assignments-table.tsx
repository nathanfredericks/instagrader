"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { ClipboardListIcon, Loader2Icon, MoreHorizontalIcon, Trash2Icon } from "lucide-react";
import { toast } from "sonner";

import { client } from "@/lib/api/client";
import { AssignmentStatusBadge } from "@/components/assignment-status-badge";
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
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AssignmentList } from "@/lib/types";

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function AssignmentRowActions({
  assignment,
  deletingId,
  onDelete,
}: {
  assignment: AssignmentList;
  deletingId: string | null;
  onDelete: (id: string) => void;
}) {
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon">
            <MoreHorizontalIcon />
            <span className="sr-only">Actions</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            variant="destructive"
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
            <AlertDialogTitle>Delete assignment?</AlertDialogTitle>
            <AlertDialogDescription>
              This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={deletingId === assignment.id}
              onClick={() => onDelete(assignment.id)}
            >
              {deletingId === assignment.id ? (
                <Loader2Icon className="animate-spin" />
              ) : (
                <Trash2Icon />
              )}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export function AssignmentsTable({
  initialAssignments,
}: {
  initialAssignments: AssignmentList[];
}) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { data: assignments, mutate } = useSWR(
    "/api/assignments/",
    async () => {
      const { data } = await client.GET("/api/assignments/");
      return data ?? [];
    },
    { fallbackData: initialAssignments, refreshInterval: 5000 }
  );

  async function handleDelete(assignmentId: string) {
    setDeletingId(assignmentId);

    try {
      const { response } = await client.DELETE(
        "/api/assignments/{assignment_id}/",
        {
          params: { path: { assignment_id: assignmentId } },
        }
      );

      if (!response.ok) {
        toast.error("Failed to delete assignment");
        return;
      }

      toast.success("Assignment deleted");
      await mutate();
    } finally {
      setDeletingId(null);
    }
  }

  if (!assignments || assignments.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
        <ClipboardListIcon className="text-muted-foreground mb-3 size-10" />
        <h3 className="text-lg font-medium">No assignments yet</h3>
        <p className="text-muted-foreground mt-1 text-sm">
          Create your first assignment to start grading essays.
        </p>
        <Button asChild className="mt-4">
          <Link href="/assignments/new">New assignment</Link>
        </Button>
      </div>
    );
  }

  return (
    <>
      {/* Mobile card layout */}
      <div className="lg:hidden space-y-3">
        {assignments.map((assignment) => (
          <Card key={assignment.id}>
            <CardHeader>
              <CardTitle className="truncate">
                <Link
                  href={`/assignments/${assignment.id}`}
                  className="hover:underline"
                  title={assignment.title}
                >
                  {assignment.title}
                </Link>
              </CardTitle>
              <CardAction>
                <AssignmentRowActions
                  assignment={assignment}
                  deletingId={deletingId}
                  onDelete={(id) => void handleDelete(id)}
                />
              </CardAction>
            </CardHeader>
            <CardContent>
              <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-sm">
                <AssignmentStatusBadge status={assignment.status} />
                <span>{assignment.essay_count} submission{assignment.essay_count !== 1 ? "s" : ""}</span>
                <span>&middot;</span>
                <span>{formatDate(assignment.created_at)}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Desktop table layout */}
      <div className="hidden lg:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Assignment Name</TableHead>
              <TableHead className="w-32">Submissions</TableHead>
              <TableHead className="w-40">Created</TableHead>
              <TableHead className="w-28">Status</TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {assignments.map((assignment) => (
              <TableRow key={assignment.id}>
                <TableCell className="max-w-0">
                  <Link
                    href={`/assignments/${assignment.id}`}
                    className="block truncate font-medium hover:underline"
                    title={assignment.title}
                  >
                    {assignment.title}
                  </Link>
                  {assignment.description ? (
                    <p className="text-muted-foreground mt-1 truncate text-xs">
                      {assignment.description}
                    </p>
                  ) : null}
                </TableCell>
                <TableCell>{assignment.essay_count}</TableCell>
                <TableCell>{formatDate(assignment.created_at)}</TableCell>
                <TableCell>
                  <AssignmentStatusBadge status={assignment.status} />
                </TableCell>
                <TableCell className="text-right">
                  <AssignmentRowActions
                    assignment={assignment}
                    deletingId={deletingId}
                    onDelete={(id) => void handleDelete(id)}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
