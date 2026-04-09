import createClient from "openapi-fetch";
import type { paths } from "./schema";
import { PUBLIC_API_URL } from "@/lib/config";

export const client = createClient<paths>({
  baseUrl: PUBLIC_API_URL,
  credentials: "include",
});

let isHandlingUnauthorized = false;

// guard flag prevents multiple simultaneous logout redirects
async function handleUnauthorized(): Promise<void> {
  if (typeof window === "undefined" || isHandlingUnauthorized) {
    return;
  }

  isHandlingUnauthorized = true;

  try {
    await fetch(`${PUBLIC_API_URL}/api/auth/logout/`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // swallow fetch errors, proceed to redirect
  }

  window.location.href = "/login";
}

client.use({
  async onResponse({ response }) {
    if (response.status === 401) {
      // fires logout without awaiting, caller still receives the 401
      void handleUnauthorized();
    }
    return response;
  },
});
