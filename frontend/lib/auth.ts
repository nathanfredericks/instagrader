import { createServerClient } from "@/lib/api/server";

export async function getCurrentUser() {
  const { cookies } = await import("next/headers");
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;

  if (!accessToken) return null;

  try {
    const client = await createServerClient();
    const { data, error } = await client.GET("/api/auth/me/");
    if (error) return null;
    return data;
  } catch {
    return null;
  }
}
