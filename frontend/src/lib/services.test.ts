import { afterEach, expect, test, vi } from "vitest";
import { appointments, approvals, availability, doctors } from "./services";

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
const reply = (body: unknown) =>
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })),
  );

test("doctor discovery sends a real natural-language search to the API", async () => {
  reply({ status: "success", message: "Done", doctors: [] });
  expect((await doctors.search("Cardiology in Karachi")).doctors).toEqual([]);
  const [url, options] = vi.mocked(fetch).mock.calls[0];
  expect(url).toContain("/doctors/search");
  expect(JSON.parse(String(options?.body)).message).toBe(
    "Cardiology in Karachi",
  );
});

test("availability request includes the patient timezone", async () => {
  reply({ status: "success", message: "Done", slots: [] });
  await availability.search("Tomorrow with Dr Khan");
  const [, options] = vi.mocked(fetch).mock.calls[0];
  expect(JSON.parse(String(options?.body)).user_timezone).toBeTruthy();
});

test("date-specific availability sends the exact doctor and selected date", async () => {
  reply({ status: "success", message: "Done", slots: [] });
  await availability.searchForDoctor("doctor-1", "2099-01-02");
  const [, options] = vi.mocked(fetch).mock.calls[0];
  expect(JSON.parse(String(options?.body))).toMatchObject({
    doctor_id: "doctor-1",
    appointment_date: "2099-01-02",
    user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  });
});

test("booking preparation sends exact doctor and slot IDs", async () => {
  reply({ status: "success", message: "Prepared", proposal: null });
  await appointments.prepareBooking("doctor-1", "slot-1");
  const [, options] = vi.mocked(fetch).mock.calls[0];
  expect(JSON.parse(String(options?.body))).toMatchObject({
    doctor_id: "doctor-1",
    slot_id: "slot-1",
  });
});

test("approval sends the explicit proposal version and decision", async () => {
  reply({
    status: "success",
    message: "Booked",
    booking_result: { status: "BOOKED" },
  });
  await approvals.booking(
    {
      booking_request_id: "request-1",
      proposal_version: 2,
      doctor_name: "Dr Khan",
      start_time: "2026-11-05T10:00:00Z",
      end_time: "2026-11-05T10:30:00Z",
      clinic_name: null,
      expires_at: "2026-11-05T09:00:00Z",
      reason: null,
    },
    "APPROVE",
  );
  const [url, options] = vi.mocked(fetch).mock.calls[0];
  expect(url).toContain("/appointments/request-1/approve");
  expect(JSON.parse(String(options?.body))).toMatchObject({
    booking_request_id: "request-1",
    proposal_version: 2,
    decision: "APPROVE",
  });
});
