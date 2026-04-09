"use client";

import useSWR from "swr";
import { client } from "@/lib/api/client";
import { CreateAssignmentForm } from "@/components/create-assignment-form";
import type { RubricList } from "@/lib/types";

export function NewAssignmentContent({
  initialRubrics,
}: {
  initialRubrics: RubricList[];
}) {
  const { data: rubrics } = useSWR(
    "/api/rubrics/",
    async () => {
      const { data } = await client.GET("/api/rubrics/");
      return data ?? [];
    },
    { fallbackData: initialRubrics, refreshInterval: 5000 }
  );

  return <CreateAssignmentForm rubrics={rubrics ?? []} />;
}
