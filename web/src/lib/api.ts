import { getSupabase } from "@/lib/supabase";

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000").replace(/\/$/, "");

function detailOf(data: unknown): string | null {
  if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") {
    return data.detail;
  }
  return null;
}

// Calls the backend with the signed-in user's Supabase access token and returns the parsed JSON body.
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = (await getSupabase()?.auth.getSession())?.data.session;
  if (!session) throw new Error("Your session has expired. Sign in again.");

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${session.access_token}`);
  if (init.body) headers.set("Content-Type", "application/json");

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new Error("Could not reach the server. Is the backend running?");
  }
  const data: unknown = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(detailOf(data) ?? `Request failed (HTTP ${response.status}).`);
  }
  return data as T;
}
