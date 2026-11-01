import { api, post, ApiError } from "./api-client";
import type {
  Appointment,
  BookingProposal,
  CancellationProposal,
  Conversation,
  ConversationDetail,
  Doctor,
  KnowledgeAnswer,
  MemoryItem,
  ReschedulingProposal,
  Slot,
} from "../types/api";

type AgentResult<T> = {
  status: string;
  message: string;
  error: string | null;
} & T;
function success<T extends { status: string; message: string }>(result: T): T {
  if (result.status !== "success")
    throw new ApiError(
      result.message || "The request could not be completed.",
      409,
    );
  return result;
}
export const doctors = {
  search: async (message: string, signal?: AbortSignal) =>
    success(
      await post<AgentResult<{ doctors: Doctor[] }>>(
        "/doctors/search",
        { message },
        signal,
      ),
    ),
};
export const availability = {
  search: async (message: string, signal?: AbortSignal) =>
    success(
      await post<AgentResult<{ slots: Slot[] }>>(
        "/availability/search",
        {
          message,
          user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        },
        signal,
      ),
    ),
};
export const appointments = {
  list: () => api<Appointment[]>("/appointments"),
  detail: (id: string) => api<Appointment>(`/appointments/${id}`),
  prepareBooking: async (doctor_id: string, slot_id: string) =>
    success(
      await post<AgentResult<{ proposal: BookingProposal | null }>>(
        "/appointments/prepare",
        {
          doctor_id,
          slot_id,
          message: "Book this selected appointment slot",
          user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        },
      ),
    ),
  prepareCancellation: async (appointment_id: string) =>
    success(
      await post<AgentResult<{ proposal: CancellationProposal | null }>>(
        "/appointments/cancel/prepare",
        { appointment_id, message: "Cancel this appointment" },
      ),
    ),
  prepareRescheduling: async (appointment_id: string, new_slot_id: string) =>
    success(
      await post<AgentResult<{ proposal: ReschedulingProposal | null }>>(
        "/appointments/reschedule/prepare",
        {
          appointment_id,
          new_slot_id,
          message: "Reschedule this appointment to the selected slot",
        },
      ),
    ),
};
export const approvals = {
  booking: async (p: BookingProposal, decision: "APPROVE" | "REJECT") =>
    success(
      await post<
        AgentResult<{
          booking_result?: { status: string; appointment_id?: string };
        }>
      >(`/appointments/${p.booking_request_id}/approve`, {
        booking_request_id: p.booking_request_id,
        proposal_version: p.proposal_version,
        decision,
      }),
    ),
  cancellation: async (
    p: CancellationProposal,
    decision: "APPROVE" | "REJECT",
  ) =>
    success(
      await post<
        AgentResult<{
          cancellation_result?: { status: string; appointment_id?: string };
        }>
      >(`/appointments/cancel/${p.cancellation_request_id}/approve`, {
        cancellation_request_id: p.cancellation_request_id,
        proposal_version: p.proposal_version,
        decision,
      }),
    ),
  rescheduling: async (
    p: ReschedulingProposal,
    decision: "APPROVE" | "REJECT",
  ) =>
    success(
      await post<
        AgentResult<{
          rescheduling_result?: { status: string; appointment_id?: string };
        }>
      >(`/appointments/reschedule/${p.reschedule_request_id}/approve`, {
        reschedule_request_id: p.reschedule_request_id,
        proposal_version: p.proposal_version,
        decision,
      }),
    ),
};
export const conversations = {
  list: async () =>
    (await api<{ conversations: Conversation[] }>("/conversations"))
      .conversations,
  create: () =>
    post<Conversation>("/conversations", { title: "New conversation" }),
  detail: (id: string) => api<ConversationDetail>(`/conversations/${id}`),
  remove: (id: string) => api(`/conversations/${id}`, { method: "DELETE" }),
  memories: async () =>
    (await api<{ memories: MemoryItem[] }>("/conversations/memory")).memories,
  addMemory: (key: string, value: string) =>
    post<MemoryItem>("/conversations/memory", { key, value }),
  removeMemory: (id: string) =>
    api(`/conversations/memory/${id}`, { method: "DELETE" }),
};
export const chat = {
  send: (session_id: string, message: string) =>
    post<{
      message: string;
      action_type: string | null;
      requires_hitl: boolean;
    }>("/chat", { session_id, message }),
};
export const knowledge = {
  search: (query: string) =>
    post<KnowledgeAnswer>("/knowledge/search", { query }),
};
export type PatientProfile = {
  name: string;
  email: string;
  phone: string | null;
  timezone: string;
};
export const patients = {
  me: () => api<PatientProfile>("/patients/me"),
  setup: (body: { name: string; phone?: string; timezone: string }) =>
    post<PatientProfile>("/patients/me", body),
};
