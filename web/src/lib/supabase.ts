import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

// Lazy so `next build` works without the Supabase variables; null means sign-in isn't configured.
export function getSupabase(): SupabaseClient | null {
  if (client) return client;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !publishableKey) return null;

  client = createClient(url, publishableKey);
  return client;
}
