"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { z } from "zod/v4";
import { loginSchema, signupSchema } from "@/lib/validations/auth";
import { API_URL } from "@/lib/config";
import { forwardCookies } from "@/lib/actions/cookies";

export type AuthActionState = {
  error?: string;
  fieldErrors?: Record<string, string[]>;
  values?: Record<string, string>;
} | null;

export async function loginAction(
  _prevState: AuthActionState,
  formData: FormData
): Promise<AuthActionState> {
  const rawData = {
    email: formData.get("email") as string,
    password: formData.get("password") as string,
  };

  const result = loginSchema.safeParse(rawData);
  if (!result.success) {
    return {
      fieldErrors: z.flattenError(result.error).fieldErrors,
      values: { email: rawData.email },
    };
  }

  try {
    const response = await fetch(`${API_URL}/api/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      return {
        error: errorData?.detail ?? "Invalid email or password",
        values: { email: rawData.email },
      };
    }

    await forwardCookies(response);
  } catch {
    return {
      error: "Login failed. Please try again.",
      values: { email: rawData.email },
    };
  }

  redirect("/");
}

export async function signupAction(
  _prevState: AuthActionState,
  formData: FormData
): Promise<AuthActionState> {
  const rawData = {
    email: formData.get("email") as string,
    full_name: formData.get("full_name") as string,
    password: formData.get("password") as string,
    password_confirm: formData.get("password_confirm") as string,
  };

  const result = signupSchema.safeParse(rawData);
  if (!result.success) {
    return {
      fieldErrors: z.flattenError(result.error).fieldErrors,
      values: { email: rawData.email, full_name: rawData.full_name },
    };
  }

  try {
    // register doesnt set cookies, so we login immediately after
    const registerResponse = await fetch(`${API_URL}/api/auth/register/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.data),
    });

    if (!registerResponse.ok) {
      // backend returns field-level errors as {field: [messages]}
      const errorData = await registerResponse.json().catch(() => null);
      if (errorData && typeof errorData === "object" && !Array.isArray(errorData)) {
        const fieldErrors: Record<string, string[]> = {};
        for (const [key, value] of Object.entries(errorData)) {
          fieldErrors[key] = Array.isArray(value) ? value : [String(value)];
        }
        if (Object.keys(fieldErrors).length > 0) {
          return {
            fieldErrors,
            values: { email: rawData.email, full_name: rawData.full_name },
          };
        }
      }
      return {
        error: "Registration failed. Please try again.",
        values: { email: rawData.email, full_name: rawData.full_name },
      };
    }

    const loginResponse = await fetch(`${API_URL}/api/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: result.data.email,
        password: result.data.password,
      }),
    });

    if (!loginResponse.ok) {
      return {
        error: "Account created but login failed. Please log in manually.",
      };
    }

    await forwardCookies(loginResponse);
  } catch {
    return {
      error: "Registration failed. Please try again.",
      values: { email: rawData.email, full_name: rawData.full_name },
    };
  }

  redirect("/");
}

export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;
  const refreshToken = cookieStore.get("refresh_token")?.value;

  const cookieParts: string[] = [];
  if (accessToken) cookieParts.push(`access_token=${accessToken}`);
  if (refreshToken) cookieParts.push(`refresh_token=${refreshToken}`);

  try {
    await fetch(`${API_URL}/api/auth/logout/`, {
      method: "POST",
      headers: {
        Cookie: cookieParts.join("; "),
      },
    });
  } catch {
    // swallow fetch errors, we redirect regardless
  }

  cookieStore.delete("access_token");
  cookieStore.delete("refresh_token");

  redirect("/login");
}
