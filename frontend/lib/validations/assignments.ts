import { z } from "zod/v4";

export const createAssignmentSchema = z.object({
  title: z.string().min(1, "Assignment name is required"),
  description: z.string().optional(),
  prompt: z.string().min(1, "Prompt is required"),
  source_text: z.string().optional(),
  rubric: z.string().uuid("Please select a rubric"),
});

export const updateAssignmentMetadataSchema = z.object({
  assignment_id: z.uuid(),
  title: z.string().min(1, "Assignment name is required"),
  description: z.string().optional(),
});
