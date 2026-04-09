"use client";

import { useActionState, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CircleAlert, DownloadIcon, MoreHorizontalIcon, PencilIcon } from "lucide-react";
import { toast } from "sonner";

import {
  updateAssignmentMetadataAction,
  type AssignmentActionState,
} from "@/lib/actions/assignments";
import { PUBLIC_API_URL } from "@/lib/config";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DeleteAssignmentButton } from "@/components/delete-assignment-button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import type { AssignmentStatus } from "@/lib/types";

export function AssignmentActions({
  assignmentId,
  title,
  description,
  status,
}: {
  assignmentId: string;
  title: string;
  description?: string;
  status?: AssignmentStatus;
}) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);

  const [state, formAction, pending] = useActionState<
    AssignmentActionState,
    FormData
  >(updateAssignmentMetadataAction, null);

  useEffect(() => {
    if (!state?.success) {
      return;
    }

    toast.success("Assignment updated");
    // defers router.refresh to next tick to avoid state conflicts with sheet close
    const timerId = window.setTimeout(() => {
      setEditOpen(false);
      router.refresh();
    }, 0);

    return () => window.clearTimeout(timerId);
  }, [router, state?.success]);

  const handleExportCsv = useCallback(async () => {
    const response = await fetch(
      `${PUBLIC_API_URL}/api/assignments/${assignmentId}/export/csv/`,
      { credentials: "include" }
    );
    if (!response.ok) return;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [assignmentId, title]);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="icon">
            <MoreHorizontalIcon />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => setEditOpen(true)}>
            <PencilIcon />
            Edit
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => void handleExportCsv()}>
            <DownloadIcon />
            Export CSV
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DeleteAssignmentButton assignmentId={assignmentId} />
        </DropdownMenuContent>
      </DropdownMenu>

      <Sheet open={editOpen} onOpenChange={setEditOpen}>
        <SheetContent side="right">
          <form action={formAction} className="flex h-full flex-col">
            <SheetHeader>
              <SheetTitle>Edit assignment</SheetTitle>
              <SheetDescription>
                Update assignment name and description.
              </SheetDescription>
            </SheetHeader>

            <div className="flex-1 overflow-y-auto p-4">
              <FieldGroup>
                {state?.error ? (
                  <Alert variant="destructive">
                    <CircleAlert />
                    <AlertDescription>{state.error}</AlertDescription>
                  </Alert>
                ) : null}
                <input
                  type="hidden"
                  name="assignment_id"
                  value={assignmentId}
                />
                <Field>
                  <FieldLabel htmlFor="edit-assignment-title">
                    Assignment name
                  </FieldLabel>
                  <Input
                    id="edit-assignment-title"
                    name="title"
                    defaultValue={state?.values?.title ?? title}
                    required
                  />
                  {state?.fieldErrors?.title ? (
                    <FieldError>{state.fieldErrors.title.join(", ")}</FieldError>
                  ) : null}
                </Field>
                <Field>
                  <FieldLabel htmlFor="edit-assignment-description">
                    Description
                  </FieldLabel>
                  <Textarea
                    id="edit-assignment-description"
                    name="description"
                    rows={4}
                    defaultValue={state?.values?.description ?? (description ?? "")}
                  />
                  {state?.fieldErrors?.description ? (
                    <FieldError>
                      {state.fieldErrors.description.join(", ")}
                    </FieldError>
                  ) : null}
                </Field>
              </FieldGroup>
            </div>

            <SheetFooter>
              <Button type="submit" disabled={pending}>
                {pending ? "Saving..." : "Save changes"}
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>
    </>
  );
}
