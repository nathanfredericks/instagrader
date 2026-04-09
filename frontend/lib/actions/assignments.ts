"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod/v4";
import {
  createAssignmentSchema,
  updateAssignmentMetadataSchema,
} from "@/lib/validations/assignments";
import { createServerClient } from "@/lib/api/server";
import { API_URL } from "@/lib/config";

export type AssignmentActionState = {
  success?: boolean;
  error?: string;
  fieldErrors?: Record<string, string[]>;
  values?: Record<string, string>;
} | null;

export async function createAssignmentAction(
  _prevState: AssignmentActionState,
  formData: FormData
): Promise<AssignmentActionState> {
  const rawData = {
    title: formData.get("title") as string,
    description: (formData.get("description") as string) || undefined,
    prompt: formData.get("prompt") as string,
    source_text: (formData.get("source_text") as string) || undefined,
    rubric: formData.get("rubric") as string,
  };

  const result = createAssignmentSchema.safeParse(rawData);
  if (!result.success) {
    return {
      fieldErrors: z.flattenError(result.error).fieldErrors,
      values: {
        title: rawData.title ?? "",
        description: rawData.description ?? "",
        prompt: rawData.prompt ?? "",
        source_text: rawData.source_text ?? "",
        rubric: rawData.rubric ?? "",
      },
    };
  }

  const client = await createServerClient();
  // works around openapi-fetch inference not narrowing the body type
  const { data, error, response } = await client.POST("/api/assignments/", {
    body: result.data as never,
  });

  if (!response.ok || !data) {
    if (error) {
      const fieldErrors: Record<string, string[]> = {};
      for (const [key, value] of Object.entries(error)) {
        fieldErrors[key] = Array.isArray(value) ? value : [String(value)];
      }
      if (Object.keys(fieldErrors).length > 0) {
        return {
          fieldErrors,
          values: {
            title: rawData.title ?? "",
            description: rawData.description ?? "",
            prompt: rawData.prompt ?? "",
            source_text: rawData.source_text ?? "",
            rubric: rawData.rubric ?? "",
          },
        };
      }
    }
    return {
      error: "Failed to create assignment. Please try again.",
      values: {
        title: rawData.title ?? "",
        description: rawData.description ?? "",
        prompt: rawData.prompt ?? "",
        source_text: rawData.source_text ?? "",
        rubric: rawData.rubric ?? "",
      },
    };
  }

  redirect(`/assignments/${data.id}`);
}

export async function updateAssignmentMetadataAction(
  _prevState: AssignmentActionState,
  formData: FormData
): Promise<AssignmentActionState> {
  const rawData = {
    assignment_id: formData.get("assignment_id") as string,
    title: formData.get("title") as string,
    description: (formData.get("description") as string) || undefined,
  };

  const result = updateAssignmentMetadataSchema.safeParse(rawData);
  if (!result.success) {
    return {
      fieldErrors: z.flattenError(result.error).fieldErrors,
      values: {
        assignment_id: rawData.assignment_id ?? "",
        title: rawData.title ?? "",
        description: rawData.description ?? "",
      },
    };
  }

  const client = await createServerClient();
  const { data, error, response } = await client.PATCH(
    "/api/assignments/{assignment_id}/",
    {
      params: { path: { assignment_id: result.data.assignment_id } },
      body: {
        title: result.data.title,
        description: result.data.description ?? "",
      },
    }
  );

  if (!response.ok || !data) {
    if (error) {
      const fieldErrors: Record<string, string[]> = {};
      for (const [key, value] of Object.entries(error)) {
        fieldErrors[key] = Array.isArray(value) ? value : [String(value)];
      }
      if (Object.keys(fieldErrors).length > 0) {
        return {
          fieldErrors,
          values: {
            assignment_id: rawData.assignment_id ?? "",
            title: rawData.title ?? "",
            description: rawData.description ?? "",
          },
        };
      }
    }
    return {
      error: "Failed to update assignment. Please try again.",
      values: {
        assignment_id: rawData.assignment_id ?? "",
        title: rawData.title ?? "",
        description: rawData.description ?? "",
      },
    };
  }

  revalidatePath(`/assignments/${result.data.assignment_id}`);
  return {
    success: true,
    values: {
      assignment_id: result.data.assignment_id,
      title: data.title,
      description: data.description ?? "",
    },
  };
}

export async function deleteAssignmentAction(assignmentId: string): Promise<{ success?: boolean; error?: string }> {
  const client = await createServerClient();
  const { response } = await client.DELETE("/api/assignments/{assignment_id}/", {
    params: { path: { assignment_id: assignmentId } },
  });

  if (!response.ok) {
    return { error: "Failed to delete assignment." };
  }

  return { success: true };
}

export async function deleteEssayAction(
  assignmentId: string,
  essayId: string
): Promise<{ success?: boolean; error?: string }> {
  const client = await createServerClient();
  const { response } = await client.DELETE("/api/essays/{essay_id}/delete/", {
    params: { path: { essay_id: essayId } },
  });

  if (!response.ok) {
    return { error: "Failed to delete essay." };
  }

  return { success: true };
}

export async function retryEssayAction(
  essayId: string
): Promise<{ success?: boolean; error?: string }> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;
  const refreshToken = cookieStore.get("refresh_token")?.value;

  const cookieParts: string[] = [];
  if (accessToken) cookieParts.push(`access_token=${accessToken}`);
  if (refreshToken) cookieParts.push(`refresh_token=${refreshToken}`);

  // uses raw fetch instead of server client to forward cookies manually for the POST
  const response = await fetch(`${API_URL}/api/essays/${essayId}/retry/`, {
    method: "POST",
    headers: {
      Cookie: cookieParts.join("; "),
    },
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    return { error: data?.detail ?? "Failed to retry essay." };
  }

  return { success: true };
}
