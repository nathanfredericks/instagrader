"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckIcon, FileIcon, Loader2Icon, PlusIcon } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { client } from "@/lib/api/client";
import type { RubricTemplateSummary } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type TemplateOption = RubricTemplateSummary | { key: "blank"; name: string; description: string; criteria_count: number; level_pattern: number[] };


export function RubricTemplateSelector({
  initialTemplates,
}: {
  initialTemplates: RubricTemplateSummary[];
}) {
  const router = useRouter();
  const [selectedKey, setSelectedKey] = useState<string>(initialTemplates[0]?.key ?? "blank");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [nameError, setNameError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const templates = useMemo<TemplateOption[]>(
    () => [
      {
        key: "blank",
        name: "Blank Rubric",
        description: "Start from scratch and define every criterion and level yourself.",
        criteria_count: 0,
        level_pattern: [],
      },
      ...initialTemplates,
    ],
    [initialTemplates]
  );

  async function handleCreate() {
    if (!name.trim()) {
      setNameError(true);
      return;
    }
    setNameError(false);
    setSubmitting(true);
    try {
      if (selectedKey === "blank") {
        const { data, response } = await client.POST("/api/rubrics/", {
          body: {
            name: name.trim(),
            description: description.trim(),
          } as never,
        });
        if (!response.ok || !data) {
          toast.error("Failed to create blank rubric.");
          return;
        }
        router.push(`/rubrics/${data.id}`);
        return;
      }

      const { data, response } = await client.POST(
        "/api/rubrics/templates/{template_key}/instantiate/",
        {
          params: { path: { template_key: selectedKey } },
          body: {
            name: name.trim(),
            description: description.trim() || undefined,
          },
        }
      );

      if (!response.ok || !data) {
        toast.error("Failed to create rubric from template.");
        return;
      }

      router.push(`/rubrics/${data.id}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <FieldGroup className="max-w-2xl">
        <Field>
          <FieldLabel htmlFor="rubric-name">Rubric name</FieldLabel>
          <Input
            id="rubric-name"
            value={name}
            className={nameError ? "ring-2 ring-destructive" : ""}
            onChange={(event) => {
              setName(event.target.value);
              if (nameError && event.target.value.trim()) setNameError(false);
            }}
          />
          {nameError && <FieldError>Rubric name is required.</FieldError>}
        </Field>
        <Field>
          <FieldLabel htmlFor="rubric-description">
            Description{" "}
            <span className="text-muted-foreground font-normal">(optional)</span>
          </FieldLabel>
          <Textarea
            id="rubric-description"
            value={description}
            rows={3}
            onChange={(event) => setDescription(event.target.value)}
          />
        </Field>
      </FieldGroup>

      <p className="text-base font-semibold text-foreground">Templates</p>

      <div className="grid gap-4 md:grid-cols-2">
        {templates.map((template) => {
          const isSelected = selectedKey === template.key;
          const isBlank = template.key === "blank";
          return (
            <Card
              key={template.key}
              role="button"
              tabIndex={0}
              onClick={() => setSelectedKey(template.key)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setSelectedKey(template.key);
                }
              }}
              size="sm"
              className={cn(
                "h-full cursor-pointer text-left transition",
                isBlank ? "border-dashed" : "",
                isSelected
                  ? "border-primary bg-primary/[0.03] ring-2 ring-primary/20"
                  : "hover:bg-muted/40"
              )}
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      {isBlank ? <FileIcon className="text-muted-foreground size-4 shrink-0" /> : null}
                      <CardTitle>{template.name}</CardTitle>
                    </div>
                    {!isBlank && (
                      <p className="text-muted-foreground mt-0.5 text-xs">
                        {template.criteria_count} {template.criteria_count === 1 ? "criterion" : "criteria"}
                      </p>
                    )}
                  </div>
                  <div
                    className={cn(
                      "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border-2 transition",
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-muted-foreground/30"
                    )}
                  >
                    {isSelected && <CheckIcon className="size-3" />}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col">
                <p className="text-muted-foreground flex-1 text-sm">{template.description}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="space-y-2">
        <Button onClick={() => void handleCreate()} disabled={submitting}>
          {submitting ? <Loader2Icon className="animate-spin" /> : <PlusIcon />}
          Create rubric
        </Button>
      </div>
    </div>
  );
}
