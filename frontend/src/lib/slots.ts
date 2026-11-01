import { format, isValid } from "date-fns";
import type { Slot } from "../types/api";

export function localToday(): string {
  return format(new Date(), "yyyy-MM-dd");
}

export function matchingSlots(
  slots: Slot[],
  doctorId: string,
  day: string,
): Slot[] {
  return slots.filter((slot) => {
    const start = new Date(slot.start_time);
    return (
      slot.doctor_id === doctorId &&
      slot.status === "AVAILABLE" &&
      isValid(start) &&
      format(start, "yyyy-MM-dd") === day
    );
  });
}
