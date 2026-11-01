import { z } from "zod";
import { api } from "./api-client";
import type { Proposal, ProposalReference } from "../types/api";

const date = z.string().refine((value) => Number.isFinite(Date.parse(value)));
const common = z.object({
  proposal_version: z.number().int().positive(),
  doctor_name: z.string(),
  expires_at: date,
});
const booking = common.extend({
  booking_request_id: z.string(),
  start_time: date,
  end_time: date,
  clinic_name: z.string().nullable(),
  reason: z.string().nullable(),
});
const cancellation = common.extend({
  cancellation_request_id: z.string(),
  appointment_start: date,
});
const rescheduling = common.extend({
  reschedule_request_id: z.string(),
  old_start_time: date,
  new_start_time: date,
});
const recordSchema = z.object({
  id: z.string(),
  action: z.enum(["BOOKING", "CANCELLATION", "RESCHEDULING"]),
  status: z.string(),
  version: z.number().int().positive(),
  expires_at: date,
  payload: z.unknown(),
});

export async function recoverProposal(
  reference: ProposalReference,
): Promise<Proposal> {
  const raw = await api<unknown>(
    `/approvals/${encodeURIComponent(reference.id)}`,
  );
  const parsed = recordSchema.safeParse(raw);
  if (!parsed.success)
    throw new Error("The request details could not be read.");
  const record = parsed.data;
  if (
    record.id !== reference.id ||
    record.action !== reference.kind.toUpperCase()
  )
    throw new Error("The request details do not match this conversation.");
  if (record.status !== "PENDING_APPROVAL")
    throw new Error("This request is no longer awaiting a decision.");
  if (new Date(record.expires_at).getTime() <= Date.now())
    throw new Error("This request has expired. Please prepare a new request.");
  const payload =
    reference.kind === "booking"
      ? booking.safeParse(record.payload)
      : reference.kind === "cancellation"
        ? cancellation.safeParse(record.payload)
        : rescheduling.safeParse(record.payload);
  if (!payload.success)
    throw new Error("The request details could not be read.");
  if (reference.kind === "booking") {
    const data = booking.parse(payload.data);
    if (data.booking_request_id !== reference.id)
      throw new Error("The request details do not match this conversation.");
    return {
      kind: "booking",
      data: {
        ...data,
        proposal_version: record.version,
        expires_at: record.expires_at,
      },
    };
  }
  if (reference.kind === "cancellation") {
    const data = cancellation.parse(payload.data);
    if (data.cancellation_request_id !== reference.id)
      throw new Error("The request details do not match this conversation.");
    return {
      kind: "cancellation",
      data: {
        ...data,
        proposal_version: record.version,
        expires_at: record.expires_at,
      },
    };
  }
  const data = rescheduling.parse(payload.data);
  if (data.reschedule_request_id !== reference.id)
    throw new Error("The request details do not match this conversation.");
  return {
    kind: "rescheduling",
    data: {
      ...data,
      proposal_version: record.version,
      expires_at: record.expires_at,
    },
  };
}
