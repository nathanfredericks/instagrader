/**
 * Server-side API URL — used in Server Actions, server components, and middleware.
 * Falls back to localhost for local development.
 */
export const API_URL = process.env.API_URL || "http://localhost:8000";

/**
 * Client-side API URL — uses the NEXT_PUBLIC_ prefix so Next.js
 * inlines it into the browser bundle.
 */
export const PUBLIC_API_URL =
  process.env.NEXT_PUBLIC_API_URL || "";
