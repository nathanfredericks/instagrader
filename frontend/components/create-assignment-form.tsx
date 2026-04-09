"use client";

import Link from "next/link";
import { useActionState } from "react";
import { CircleAlert } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  createAssignmentAction,
  type AssignmentActionState,
} from "@/lib/actions/assignments";
import type { RubricList } from "@/lib/types";

export function CreateAssignmentForm({ rubrics }: { rubrics: RubricList[] }) {
  const [state, formAction, pending] = useActionState<
    AssignmentActionState,
    FormData
  >(createAssignmentAction, null);

  return (
    <form action={formAction} className="max-w-2xl">
      <FieldGroup>
        {state?.error && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertDescription>{state.error}</AlertDescription>
          </Alert>
        )}
        <Field>
          <FieldLabel htmlFor="title">Assignment name</FieldLabel>
          <Input
            id="title"
            name="title"
            defaultValue={state?.values?.title ?? ""}
            required
          />
          {state?.fieldErrors?.title && (
            <FieldError>{state.fieldErrors.title.join(", ")}</FieldError>
          )}
        </Field>
        <Field>
          <FieldLabel htmlFor="description">
            Description{" "}
            <span className="text-muted-foreground font-normal">
              (optional)
            </span>
          </FieldLabel>
          <Textarea
            id="description"
            name="description"
            rows={3}
            defaultValue={state?.values?.description ?? ""}
          />
          {state?.fieldErrors?.description && (
            <FieldError>{state.fieldErrors.description.join(", ")}</FieldError>
          )}
        </Field>
        <Field>
          <FieldLabel htmlFor="prompt">Prompt</FieldLabel>
          <Textarea
            id="prompt"
            name="prompt"
            rows={4}
            defaultValue={state?.values?.prompt ?? ""}
            required
          />
          <FieldDescription>
            The writing assignment prompt that the AI will use to evaluate
            essays.
          </FieldDescription>
          {state?.fieldErrors?.prompt && (
            <FieldError>{state.fieldErrors.prompt.join(", ")}</FieldError>
          )}
        </Field>
        <Field>
          <FieldLabel htmlFor="source_text">
            Source text{" "}
            <span className="text-muted-foreground font-normal">
              (optional)
            </span>
          </FieldLabel>
          <Textarea
            id="source_text"
            name="source_text"
            rows={4}
            defaultValue={state?.values?.source_text ?? ""}
          />
          <FieldDescription>
            Reference material that essays should be based on.
          </FieldDescription>
          {state?.fieldErrors?.source_text && (
            <FieldError>
              {state.fieldErrors.source_text.join(", ")}
            </FieldError>
          )}
        </Field>
        <Field>
          <FieldLabel>Rubric</FieldLabel>
          {rubrics.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No rubrics yet.{" "}
              <Link
                href="/rubrics/new"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline underline-offset-4"
              >
                Create new
              </Link>
            </p>
          ) : (
            <Select name="rubric" defaultValue={state?.values?.rubric}>
              <SelectTrigger>
                <SelectValue placeholder="Select a rubric" />
              </SelectTrigger>
              <SelectContent>
                {rubrics.map((r) => (
                  <SelectItem key={r.id} value={r.id}>
                    {r.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {state?.fieldErrors?.rubric && (
            <FieldError>{state.fieldErrors.rubric.join(", ")}</FieldError>
          )}
        </Field>
        <Field>
          <Button type="submit" disabled={pending || rubrics.length === 0}>
            {pending ? "Creating..." : "Create assignment"}
          </Button>
        </Field>
      </FieldGroup>
    </form>
  );
}
