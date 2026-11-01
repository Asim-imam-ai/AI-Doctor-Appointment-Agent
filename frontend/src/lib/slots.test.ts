import { expect, test } from "vitest";
import { matchingSlots } from "./slots";
import type { Slot } from "../types/api";

test("only offers available slots for the selected doctor and local date", () => {
  const day = new Date(2026, 10, 20, 10).toISOString();
  const otherDay = new Date(2026, 10, 21, 10).toISOString();
  const slot: Slot = {
    id: "available",
    doctor_id: "doctor-1",
    doctor_name: "Doctor",
    specialty: null,
    clinic_name: null,
    location: null,
    start_time: day,
    end_time: day,
    timezone: "UTC",
    status: "AVAILABLE",
  };
  const result = matchingSlots(
    [
      slot,
      { ...slot, id: "wrong-day", start_time: otherDay },
      { ...slot, id: "wrong-doctor", doctor_id: "doctor-2" },
      { ...slot, id: "booked", status: "BOOKED" },
      { ...slot, id: "invalid", start_time: "not-a-date" },
    ],
    "doctor-1",
    "2026-11-20",
  );
  expect(result.map((item) => item.id)).toEqual(["available"]);
});
