import { afterEach, expect, test, vi } from "vitest";
import { api, ApiError, post } from "./api-client";
import { supabase } from "./supabase";

vi.mock("./supabase", () => ({
  supabase: {
    auth: {
      getSession: async () => ({
        data: { session: { access_token: "test-token" } },
      }),
      signOut: vi.fn(),
    },
  },
}));
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

test("uses the development proxy for authenticated patient requests", async () => {
  vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:8000");
  const fetchMock = vi.fn(async () => new Response(JSON.stringify({ name: "Patient" })));
  vi.stubGlobal("fetch", fetchMock);
  await api("/patients/me");
  const [url, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe("/api/v1/patients/me");
  expect((options.headers as Record<string, string>).Authorization).toBe("Bearer test-token");
});

test("attaches the authenticated bearer token to search requests", async () => {
  const fetchMock = vi.fn(
    async () =>
      new Response(JSON.stringify({ doctors: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
  );
  vi.stubGlobal("fetch", fetchMock);
  await post("/doctors/search", { message: "cardiology" });
  expect(fetchMock).toHaveBeenCalledOnce();
  const [url, options] = fetchMock.mock.calls[0] as unknown as [
    string,
    RequestInit,
  ];
  expect(url).toContain("/api/v1/doctors/search");
  expect((options.headers as Record<string, string>).Authorization).toBe(
    "Bearer test-token",
  );
  expect(options.body).toBe(JSON.stringify({ message: "cardiology" }));
});

test("turns appointment conflicts into a patient-safe error", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify({ detail: "internal database detail" }), {
          status: 409,
        }),
    ),
  );
  await expect(api("/appointments/prepare")).rejects.toMatchObject({
    status: 409,
    message: "This request conflicts with the current appointment state.",
  } satisfies Partial<ApiError>);
});

test("signs out when the backend reports an expired session", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(null, { status: 401 })),
  );
  await expect(api("/appointments")).rejects.toMatchObject({ status: 401 });
  expect(supabase?.auth.signOut).toHaveBeenCalledOnce();
});

test("preserves cancellation when an outdated search is aborted", async () => {
  const abortError = new DOMException("Aborted", "AbortError");
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      throw abortError;
    }),
  );
  await expect(post("/doctors/search", { message: "doctor" })).rejects.toBe(
    abortError,
  );
});
