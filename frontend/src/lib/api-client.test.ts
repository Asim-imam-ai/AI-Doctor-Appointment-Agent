import { afterEach, expect, test, vi } from "vitest";
import { api, ApiError, post } from "./api-client";

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
afterEach(() => vi.unstubAllGlobals());

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
