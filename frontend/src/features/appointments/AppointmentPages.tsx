import { useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarDays } from "lucide-react";
import { useAuth } from "../../lib/auth";
import { appointments, availability } from "../../lib/services";
import {
  PageHeader,
  LoadingState,
  ErrorState,
  EmptyState,
  ProposalDialog,
  DateText,
} from "../../components/common";
import type { Appointment, Proposal, Slot } from "../../types/api";
const date = (value: string) => <DateText value={value} />;
export function BookingPage() {
  const { doctorId, slotId } = useParams();
  const state = useLocation().state as { slot?: Slot } | null;
  const candidate = state?.slot;
  const selected =
    candidate && candidate.id === slotId && candidate.doctor_id === doctorId
      ? candidate
      : null;
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const mutation = useMutation({
    mutationFn: () => appointments.prepareBooking(doctorId!, slotId!),
    onSuccess: (result) => {
      if (result.proposal)
        setProposal({ kind: "booking", data: result.proposal });
    },
  });
  return (
    <>
      <PageHeader
        eyebrow="ONE STEP BEFORE BOOKING"
        title="Review your appointment"
        description="Preparing a proposal does not book the appointment. You’ll confirm the details before anything changes."
      />
      <div className="card details-card">
        {selected && (
          <>
            <h2>{selected.doctor_name}</h2>
            {selected.specialty && <p>{selected.specialty}</p>}
            <p>
              {date(selected.start_time)} ·{" "}
              {Intl.DateTimeFormat().resolvedOptions().timeZone}
            </p>
            {(selected.clinic_name || selected.location) && (
              <p>
                {[selected.clinic_name, selected.location]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            )}
          </>
        )}
        <p>
          Selected doctor and time are checked against live availability when
          you prepare your request.
        </p>
        <button
          className="button"
          disabled={mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? "Preparing…" : "Prepare booking request"}
        </button>
        {mutation.isError && (
          <p role="alert" className="error-text">
            {(mutation.error as Error).message}
          </p>
        )}
        {mutation.isError && (
          <Link className="text-button" to={`/availability/${doctorId}`}>
            Find another time
          </Link>
        )}
        {mutation.data && !mutation.data.proposal && (
          <p role="alert">
            No booking proposal was returned. Try another slot.
          </p>
        )}
      </div>
      <ProposalDialog proposal={proposal} onClose={() => setProposal(null)} />
    </>
  );
}
export function AppointmentCard({
  appointment: a,
}: {
  appointment: Appointment;
}) {
  return (
    <article className="card appointment-card">
      <div className="card-top">
        <span className="status-badge">{a.status}</span>
        <CalendarDays size={20} />
      </div>
      <h3>Doctor appointment</h3>
      <p>{date(a.start_time)}</p>
      <Link to={`/appointments/${a.id}`} className="text-button">
        View details <ArrowRight size={16} />
      </Link>
    </article>
  );
}
export function AppointmentsPage() {
  const [now] = useState(() => Date.now());
  const { session } = useAuth();
  const query = useQuery({
    queryKey: ["appointments", session?.user.id],
    queryFn: appointments.list,
  });
  const upcoming =
    query.data
      ?.filter(
        (a) =>
          ["PENDING", "CONFIRMED", "RESCHEDULED"].includes(a.status) &&
          new Date(a.start_time).getTime() >= now,
      )
      .sort((a, b) => a.start_time.localeCompare(b.start_time)) ?? [];
  const history =
    query.data
      ?.filter((a) => !upcoming.some((item) => item.id === a.id))
      .sort((a, b) => b.start_time.localeCompare(a.start_time)) ?? [];
  return (
    <>
      <PageHeader
        eyebrow="YOUR VISITS"
        title="Appointments"
        description="View upcoming visits and previous appointment activity."
      />
      {query.isLoading ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState
          message="Appointments could not be loaded."
          retry={() => void query.refetch()}
        />
      ) : query.data?.length ? (
        <>
          <div className="section-heading">
            <h2>Upcoming</h2>
            <span>{upcoming.length}</span>
          </div>
          {upcoming.length ? (
            <div className="card-grid">
              {upcoming.map((a) => (
                <AppointmentCard key={a.id} appointment={a} />
              ))}
            </div>
          ) : (
            <EmptyState>No upcoming appointments.</EmptyState>
          )}
          <div className="section-heading">
            <h2>Previous activity</h2>
            <span>{history.length}</span>
          </div>
          {history.length ? (
            <div className="card-grid">
              {history.map((a) => (
                <AppointmentCard key={a.id} appointment={a} />
              ))}
            </div>
          ) : (
            <EmptyState>No previous appointments.</EmptyState>
          )}
        </>
      ) : (
        <EmptyState>
          No appointments yet. <Link to="/doctors">Find a doctor</Link> to
          begin.
        </EmptyState>
      )}
    </>
  );
}
export function AppointmentDetails() {
  const { id } = useParams();
  const query = useQuery({
    queryKey: ["appointment", id],
    queryFn: () => appointments.detail(id!),
    enabled: Boolean(id),
  });
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [day, setDay] = useState("");
  const [slot, setSlot] = useState<Slot | null>(null);
  const [search, setSearch] = useState(false);
  const available = useQuery({
    queryKey: ["availability", query.data?.doctor_id, day],
    queryFn: () =>
      availability.search(
        `Available appointments for doctor ${query.data!.doctor_id} on ${day}`,
      ),
    enabled: search && Boolean(day) && Boolean(query.data),
  });
  const cancel = useMutation({
    mutationFn: () => appointments.prepareCancellation(id!),
    onSuccess: (r) => {
      if (r.proposal) setProposal({ kind: "cancellation", data: r.proposal });
    },
  });
  const move = useMutation({
    mutationFn: () => appointments.prepareRescheduling(id!, slot!.id),
    onSuccess: (r) => {
      if (r.proposal) setProposal({ kind: "rescheduling", data: r.proposal });
    },
  });
  const a = query.data;
  return (
    <>
      <Link className="back-link" to="/appointments">
        ← Back to appointments
      </Link>
      {query.isLoading ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState message="Appointment could not be loaded." />
      ) : (
        a && (
          <>
            <PageHeader
              eyebrow="APPOINTMENT DETAILS"
              title="Your appointment"
              description="Manage this visit and review its current status."
            />
            <div className="card details-card">
              <span className="status-badge">{a.status}</span>
              <h2>{date(a.start_time)}</h2>
              <p>Doctor reference: {a.doctor_id}</p>
              <p>{a.reason ?? "No reason recorded"}</p>
              {!["CANCELLED", "COMPLETED", "NO_SHOW", "EXPIRED"].includes(
                a.status,
              ) && (
                <div className="actions">
                  <button
                    className="button secondary"
                    disabled={cancel.isPending}
                    onClick={() => cancel.mutate()}
                  >
                    {cancel.isPending ? "Preparing…" : "Request cancellation"}
                  </button>
                </div>
              )}
              {cancel.isError && (
                <p role="alert" className="error-text">
                  {(cancel.error as Error).message}
                </p>
              )}
            </div>
            {!["CANCELLED", "COMPLETED", "NO_SHOW", "EXPIRED"].includes(
              a.status,
            ) && (
              <section className="card details-card">
                <h2>Need a different time?</h2>
                <div className="filter-card">
                  <label>
                    New date
                    <input
                      type="date"
                      value={day}
                      min={new Date().toISOString().slice(0, 10)}
                      onChange={(e) => {
                        setDay(e.target.value);
                        setSlot(null);
                        setSearch(false);
                      }}
                    />
                  </label>
                  <button
                    className="button secondary"
                    disabled={!day}
                    onClick={() => setSearch(true)}
                  >
                    Find replacement slots
                  </button>
                </div>
                {available.isLoading && <LoadingState />}
                {available.isError && (
                  <ErrorState message={(available.error as Error).message} />
                )}
                <div className="slot-grid">
                  {available.data?.slots
                    .filter((s) => s.doctor_id === a.doctor_id)
                    .map((s) => (
                      <button
                        className={`slot-choice ${slot?.id === s.id ? "selected" : ""}`}
                        key={s.id}
                        onClick={() => setSlot(s)}
                      >
                        {date(s.start_time)}
                      </button>
                    ))}
                </div>
                {search &&
                  available.data &&
                  !available.data.slots.some(
                    (s) => s.doctor_id === a.doctor_id,
                  ) && (
                    <EmptyState>
                      No replacement slots found for that date.
                    </EmptyState>
                  )}
                {slot && (
                  <button
                    className="button"
                    disabled={move.isPending}
                    onClick={() => move.mutate()}
                  >
                    {move.isPending
                      ? "Preparing…"
                      : "Review reschedule request"}
                  </button>
                )}
                {move.isError && (
                  <p role="alert" className="error-text">
                    {(move.error as Error).message}
                  </p>
                )}
              </section>
            )}
          </>
        )
      )}
      <ProposalDialog
        proposal={proposal}
        onClose={() => {
          setProposal(null);
          void query.refetch();
        }}
      />
    </>
  );
}
