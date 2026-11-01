import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
export const configurationReady = Boolean(
  url && key && url !== "https://your-project.supabase.co",
);
export const supabase = configurationReady ? createClient(url, key) : null;
