import { NextRequest, NextResponse } from "next/server";
import { API_URL } from "@/lib/config";

const authPages = ["/login", "/signup"];

// decodes jwt payload without signature verification, treats parse failures as expired
function isTokenExpired(token: string): boolean {
  try {
    const payload = token.split(".")[1];
    const decoded = JSON.parse(atob(payload));
    return decoded.exp < Date.now() / 1000;
  } catch {
    return true;
  }
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const rawAccessToken = request.cookies.get("access_token")?.value;
  const accessToken =
    rawAccessToken && !isTokenExpired(rawAccessToken)
      ? rawAccessToken
      : undefined;
  const refreshToken = request.cookies.get("refresh_token")?.value;
  const isAuthPage = authPages.includes(pathname);

  // check access token first, try refresh if missing, then redirect if both absent
  if (accessToken && isAuthPage) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  if (accessToken) {
    return NextResponse.next();
  }
  if (!accessToken && refreshToken) {
    try {
      const refreshResponse = await fetch(`${API_URL}/api/auth/refresh/`, {
        method: "POST",
        headers: {
          Cookie: `refresh_token=${refreshToken}`,
        },
      });

      if (refreshResponse.ok) {
        const response = isAuthPage
          ? NextResponse.redirect(new URL("/", request.url))
          : NextResponse.next();

        // middleware must manually propagate cookies since it intercepts at request layer
        const setCookieHeaders = refreshResponse.headers.getSetCookie();
        for (const cookie of setCookieHeaders) {
          response.headers.append("Set-Cookie", cookie);
        }

        return response;
      }
    } catch {
      // refresh failed, proceed to redirect logic below
    }
  }

  if (isAuthPage) {
    return NextResponse.next();
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon\\.ico|api/|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
