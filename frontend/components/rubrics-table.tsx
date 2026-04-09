"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import {
  CopyIcon,
  ListChecksIcon,
  Loader2Icon,
  MoreHorizontalIcon,
  PencilIcon,
  Trash2Icon,
} from "lucide-react";
import { toast } from "sonner";

import { client } from "@/lib/api/client";
import type { RubricList } from "@/lib/types";
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
  DropdownMenuSeparator,
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

// appends " (Copy)" unless name already ends with it, case insensitive check
function buildDuplicateName(sourceName: string): string {
  const trimmed = sourceName.trim() || "Untitled Rubric";
  if (/\s*\(copy\)$/i.test(trimmed)) {
    return trimmed;
  }
  return `${trimmed} (Copy)`;
}

function RubricRowActions({
  rubric,
  deletingId,
  onDuplicate,
  onDelete,
}: {
  rubric: RubricList;
  deletingId: string | null;
  onDuplicate: (rubric: RubricList) => void;
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
          <DropdownMenuItem asChild>
            <Link href={`/rubrics/${rubric.id}`}>
              <PencilIcon />
              Edit
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onDuplicate(rubric)}>
            <CopyIcon />
            Duplicate
          </DropdownMenuItem>
          <DropdownMenuSeparator />
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
            <AlertDialogTitle>Delete rubric?</AlertDialogTitle>
            <AlertDialogDescription>
              This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={deletingId === rubric.id}
              onClick={() => onDelete(rubric.id)}
            >
              {deletingId === rubric.id ? (
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

export function RubricsTable({
  initialRubrics,
}: {
  initialRubrics: RubricList[];
}) {
  const router = useRouter();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { data: rubrics, mutate } = useSWR(
    "/api/rubrics/",
    async () => {
      const { data } = await client.GET("/api/rubrics/");
      return data ?? [];
    },
    { fallbackData: initialRubrics, refreshInterval: 5000 }
  );

  async function handleDuplicate(rubric: RubricList) {
    const { data, response } = await client.POST(
        "/api/rubrics/{rubric_id}/duplicate/",
      {
        params: { path: { rubric_id: rubric.id } },
        body: { name: buildDuplicateName(rubric.name) },
      }
    );

    if (!response.ok || !data) {
      toast.error("Failed to duplicate rubric");
      return;
    }

    toast.success("Rubric duplicated");
    await mutate();
    router.push(`/rubrics/${data.id}`);
  }

  async function handleDelete(rubricId: string) {
    setDeletingId(rubricId);

    try {
      const { error, response } = await client.DELETE("/api/rubrics/{rubric_id}/", {
        params: { path: { rubric_id: rubricId } },
      });

      if (!response.ok) {
        const apiDetail =
          error && typeof error === "object" && "detail" in error
            ? String((error as { detail?: unknown }).detail ?? "")
            : "";
        toast.error(apiDetail || "Failed to delete rubric");
        return;
      }

      toast.success("Rubric deleted");
      await mutate();
    } finally {
      setDeletingId(null);
    }
  }

  if (!rubrics || rubrics.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
        <ListChecksIcon className="text-muted-foreground mb-3 size-10" />
        <h3 className="text-lg font-medium">No rubrics yet</h3>
        <p className="text-muted-foreground mt-1 text-sm">
          Create a rubric to start grading essays.
        </p>
        <Button asChild className="mt-4">
          <Link href="/rubrics/new">New rubric</Link>
        </Button>
      </div>
    );
  }

  return (
    <>
      {/* Mobile card layout */}
      <div className="lg:hidden space-y-3">
        {rubrics.map((rubric) => (
          <Card key={rubric.id}>
            <CardHeader>
              <CardTitle className="truncate">
                <Link
                  href={`/rubrics/${rubric.id}`}
                  className="hover:underline"
                  title={rubric.name}
                >
                  {rubric.name}
                </Link>
              </CardTitle>
              <CardAction>
                <RubricRowActions
                  rubric={rubric}
                  deletingId={deletingId}
                  onDuplicate={(item) => void handleDuplicate(item)}
                  onDelete={(id) => void handleDelete(id)}
                />
              </CardAction>
            </CardHeader>
            <CardContent>
              <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-sm">
                <span>{formatDate(rubric.updated_at)}</span>
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
              <TableHead>Rubric</TableHead>
              <TableHead className="w-40">Updated</TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rubrics.map((rubric) => (
              <TableRow key={rubric.id}>
                <TableCell className="max-w-0">
                  <Link
                    href={`/rubrics/${rubric.id}`}
                    className="block truncate font-medium hover:underline"
                    title={rubric.name}
                  >
                    {rubric.name}
                  </Link>
                  {rubric.description ? (
                    <p className="text-muted-foreground mt-1 truncate text-xs">
                      {rubric.description}
                    </p>
                  ) : null}
                </TableCell>
                <TableCell>{formatDate(rubric.updated_at)}</TableCell>
                <TableCell>
                  <RubricRowActions
                    rubric={rubric}
                    deletingId={deletingId}
                    onDuplicate={(item) => void handleDuplicate(item)}
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
