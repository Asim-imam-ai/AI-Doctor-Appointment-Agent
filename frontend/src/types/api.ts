export type Doctor = {
  id: string;
  name: string;
  specialties: string[];
  clinic_name: string | null;
  location: string | null;
  bio: string | null;
  consultation_duration: number;
  is_active: boolean;
};
export type Slot = {
  id: string;
  doctor_id: string;
  doctor_name: string;
  specialty: string | null;
  clinic_name: string | null;
  location: string | null;
  start_time: string;
  end_time: string;
  timezone: string;
  status: string;
};
export type Appointment = {
  id: string;
  doctor_id: string;
  patient_id: string;
  start_time: string;
  end_time: string;
  reason: string | null;
  status:
    | "PENDING"
    | "CONFIRMED"
    | "CANCELLED"
    | "RESCHEDULED"
    | "COMPLETED"
    | "NO_SHOW"
    | "EXPIRED";
  created_at: string;
};
export type BookingProposal = {
  booking_request_id: string;
  proposal_version: number;
  doctor_name: string;
  start_time: string;
  end_time: string;
  clinic_name: string | null;
  expires_at: string;
  reason: string | null;
};
export type CancellationProposal = {
  cancellation_request_id: string;
  proposal_version: number;
  doctor_name: string;
  appointment_start: string;
  expires_at: string;
};
export type ReschedulingProposal = {
  reschedule_request_id: string;
  proposal_version: number;
  doctor_name: string;
  old_start_time: string;
  new_start_time: string;
  expires_at: string;
};
export type Proposal =
  | { kind: "booking"; data: BookingProposal }
  | { kind: "cancellation"; data: CancellationProposal }
  | { kind: "rescheduling"; data: ReschedulingProposal };
export type ProposalReference = {
  id: string;
  kind: Proposal["kind"];
};
export type Conversation = {
  id: string;
  title: string;
  last_message_at: string;
  summary: string | null;
  status: string;
};
export type ConversationDetail = Conversation & {
  messages: Array<{
    id: string;
    role: string;
    content: string;
    created_at: string;
    proposal_reference?: ProposalReference | null;
  }>;
};
export type MemoryItem = {
  id: string;
  key: string;
  value: string;
  memory_type: string;
};
export type KnowledgeAnswer = {
  answer: string;
  grounded: boolean;
  sources: Array<{
    document_id: string;
    title: string;
    source: string;
    version: string;
  }>;
};
