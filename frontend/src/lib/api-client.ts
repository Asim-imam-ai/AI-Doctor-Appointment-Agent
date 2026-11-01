import { supabase } from "./supabase";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
const messages: Record<number, string> = {
  401: "Your session has expired. Please sign in again.",
  403: "You do not have access to this action.",
  404: "This item could not be found.",
  409: "This request conflicts with the current appointment state.",
  422: "Please check the information you entered.",
  429: "Too many requests. Please try again shortly.",
  500: "The service could not complete your request.",
};
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const { data } = (await supabase?.auth.getSession()) ?? {
    data: { session: null },
  };
  const token = data.session?.access_token;
  const base = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}/api/v1${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Could not reach the service. Check your connection and try again.",
      0,
    );
  }
  if (!response.ok) {
    if (response.status === 401) await supabase?.auth.signOut();
    throw new ApiError(
      messages[response.status] ?? "Something went wrong. Please try again.",
      response.status,
    );
  }
  if (response.status === 204) return undefined as T;
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      "The service returned an unreadable response.",
      response.status,
    );
  }
}
export function post<T>(path: string, body: unknown, signal?: AbortSignal) {
  return api<T>(path, { method: "POST", body: JSON.stringify(body), signal });
}
