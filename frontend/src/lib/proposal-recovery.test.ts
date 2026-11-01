import { afterEach, expect, test, vi } from "vitest";
import { recoverProposal } from "./proposal-recovery";

vi.mock("./supabase", () => ({
  supabase: {
    auth: {
      getSession: async () => ({
        data: { session: { access_token: "patient-token" } },
      }),
      signOut: vi.fn(),
    },
  },
}));

afterEach(() => vi.unstubAllGlobals());

const id = "301db831-b594-4faa-9c28-50f12c1d6111";
const reference = { id, kind: "booking" as const };
const record = {
  id,
  action: "BOOKING",
  status: "PENDING_APPROVAL",
  version: 2,
  expires_at: "2099-01-01T00:00:00Z",
  payload: {
    booking_request_id: id,
    proposal_version: 1,
    doctor_name: "Dr Khan",
    start_time: "2099-01-02T10:00:00Z",
    end_time: "2099-01-02T10:30:00Z",
    clinic_name: null,
    reason: null,
    expires_at: "2099-01-01T00:00:00Z",
  },
};

function reply(body: unknown, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

test("recovery reads an owned pending proposal and uses the stored version", async () => {
  reply(record);
  const result = await recoverProposal(reference);
  expect(result.kind).toBe("booking");
  expect(result.data.proposal_version).toBe(2);
  expect(vi.mocked(fetch).mock.calls[0][0]).toContain(`/approvals/${id}`);
});

test("recovery refuses decided, expired, or mismatched requests", async () => {
  reply({ ...record, status: "REJECTED" });
  await expect(recoverProposal(reference)).rejects.toThrow(
    "no longer awaiting",
  );
  reply({ ...record, expires_at: "2000-01-01T00:00:00Z" });
  await expect(recoverProposal(reference)).rejects.toThrow("expired");
  reply({
    ...record,
    payload: { ...record.payload, booking_request_id: "different" },
  });
  await expect(recoverProposal(reference)).rejects.toThrow("do not match");
  reply({ detail: "Not found" }, 404);
  await expect(recoverProposal(reference)).rejects.toMatchObject({
    status: 404,
  });
});

test.each([
  {
    kind: "cancellation" as const,
    action: "CANCELLATION",
    payload: {
      cancellation_request_id: id,
      proposal_version: 1,
      doctor_name: "Dr Khan",
      appointment_start: "2099-01-02T10:00:00Z",
      expires_at: "2099-01-01T00:00:00Z",
    },
  },
  {
    kind: "rescheduling" as const,
    action: "RESCHEDULING",
    payload: {
      reschedule_request_id: id,
      proposal_version: 1,
      doctor_name: "Dr Khan",
      old_start_time: "2099-01-02T10:00:00Z",
      new_start_time: "2099-01-03T10:00:00Z",
      expires_at: "2099-01-01T00:00:00Z",
    },
  },
])("recovers a pending $kind proposal", async ({ kind, action, payload }) => {
  reply({ ...record, action, payload });
  expect((await recoverProposal({ id, kind })).kind).toBe(kind);
});
