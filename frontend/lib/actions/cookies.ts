"use server";

import { cookies } from "next/headers";

// parses set-cookie headers from backend response into next.js cookie jar, re-joins value segments split on =
export async function forwardCookies(response: Response) {
  const setCookieHeaders = response.headers.getSetCookie();
  const cookieStore = await cookies();

  for (const setCookie of setCookieHeaders) {
    const parts = setCookie.split(";").map((p) => p.trim());
    const [nameValue] = parts;
    const [name, ...valueParts] = nameValue.split("=");
    const value = valueParts.join("=");

    const options: Record<string, unknown> = {
      path: "/",
    };
    for (const part of parts.slice(1)) {
      const [key, val] = part.split("=");
      const lowerKey = key.toLowerCase().trim();
      if (lowerKey === "max-age") options.maxAge = parseInt(val);
      if (lowerKey === "httponly") options.httpOnly = true;
      if (lowerKey === "samesite")
        options.sameSite = val.toLowerCase() as "lax" | "strict" | "none";
      if (lowerKey === "secure") options.secure = true;
      if (lowerKey === "path") options.path = val;
    }

    cookieStore.set(name, value, options);
  }
}
