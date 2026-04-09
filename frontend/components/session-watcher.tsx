"use client";

import useSWR from "swr";
import { client } from "@/lib/api/client";

export function SessionWatcher() {
  // polls /api/auth/me/ every 5s as a session keepalive, result is unused
  useSWR(
    "/api/auth/me/session",
    async () => {
      await client.GET("/api/auth/me/");
      return null;
    },
    {
      refreshInterval: 5000,
      revalidateOnFocus: false,
    }
  );

  return null;
}
