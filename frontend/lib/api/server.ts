import createClient from "openapi-fetch";
import type { paths } from "./schema";
import { cookies } from "next/headers";
import { API_URL } from "@/lib/config";

export async function createServerClient() {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;
  const refreshToken = cookieStore.get("refresh_token")?.value;

  const cookieParts: string[] = [];
  if (accessToken) cookieParts.push(`access_token=${accessToken}`);
  if (refreshToken) cookieParts.push(`refresh_token=${refreshToken}`);

  // constructs cookie header manually because server components cant use credentials: include
  return createClient<paths>({
    baseUrl: API_URL,
    headers: {
      Cookie: cookieParts.join("; "),
    },
  });
}
