import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Link } from "react-router-dom";
import { approvals } from "../lib/services";
import { Button } from "./ui/button";
import type { Proposal } from "../types/api";

export function PageHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <header className="page-header">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  );
}
export function LoadingState() {
  return (
    <div className="state" role="status">
      Loading your information…
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="state error" role="alert">
      {message}
      {retry && (
        <button onClick={retry} className="text-button">
          Try again
        </button>
      )}
    </div>
  );
}
export function EmptyState({ children }: { children: React.ReactNode }) {
  return <div className="state">{children}</div>;
}
export function DateText({ value }: { value: string }) {
  return <time dateTime={value}>{format(new Date(value), "PPp")}</time>;
}
export function ProposalDialog({
  proposal,
  onClose,
  onDecisionCompleted,
}: {
  proposal: Proposal | null;
  onClose: () => void;
  onDecisionCompleted?: () => void;
}) {
  return proposal ? (
    <ProposalDialogContent
      proposal={proposal}
      onClose={onClose}
      onDecisionCompleted={onDecisionCompleted}
    />
  ) : null;
}

function ProposalDialogContent({
  proposal,
  onClose,
  onDecisionCompleted,
}: {
  proposal: Proposal;
  onClose: () => void;
  onDecisionCompleted?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState("");
  const [appointmentId, setAppointmentId] = useState<string | null>(null);
  const query = useQueryClient();
  const p = proposal.data;
  const proposalId =
    proposal.kind === "booking"
      ? proposal.data.booking_request_id
      : proposal.kind === "cancellation"
        ? proposal.data.cancellation_request_id
        : proposal.data.reschedule_request_id;
  const time =
    proposal.kind === "booking"
      ? proposal.data.start_time
      : proposal.kind === "cancellation"
        ? proposal.data.appointment_start
        : proposal.data.new_start_time;
  async function decide(decision: "APPROVE" | "REJECT") {
    if (!proposal) return;
    setBusy(true);
    setError("");
    try {
      if (new Date(proposal.data.expires_at).getTime() <= Date.now())
        throw new Error(
          "This proposal has expired. Please prepare a new request.",
        );
      const response =
        proposal.kind === "booking"
          ? await approvals.booking(proposal.data, decision)
          : proposal.kind === "cancellation"
            ? await approvals.cancellation(proposal.data, decision)
            : await approvals.rescheduling(proposal.data, decision);
      if (decision === "APPROVE") {
        const operationResult =
          "booking_result" in response
            ? response.booking_result
            : "cancellation_result" in response
              ? response.cancellation_result
              : "rescheduling_result" in response
                ? response.rescheduling_result
                : undefined;
        if (operationResult?.status !== "BOOKED")
          throw new Error(
            "The appointment change was not confirmed. Please check your appointments.",
          );
        setAppointmentId(operationResult.appointment_id ?? null);
      }
      await query.invalidateQueries({ queryKey: ["appointments"] });
      await query.invalidateQueries({ queryKey: ["availability"] });
      setResult(response.message);
      onDecisionCompleted?.();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not complete this decision.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog.Root
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog">
          <Dialog.Title>Review {proposal.kind} request</Dialog.Title>
          <Dialog.Description>
            Confirm the details before changing your appointment.
          </Dialog.Description>
          <div className="proposal-details">
            <small>Request reference: {proposalId}</small>
            <small>
              Status: {result ? "Decision completed" : "Awaiting your decision"}
            </small>
            <strong>{p.doctor_name}</strong>
            <DateText value={time} />
            {proposal.kind === "rescheduling" && (
              <p>
                Current time: <DateText value={proposal.data.old_start_time} />
              </p>
            )}
            <small>
              Proposal expires <DateText value={p.expires_at} />
            </small>
          </div>
          {error && (
            <p role="alert" className="error-text">
              {error}
            </p>
          )}
          {result ? (
            <>
              <p role="status">{result}</p>
              {appointmentId && <p>Appointment reference: {appointmentId}</p>}
              {appointmentId && (
                <Link
                  className="text-button"
                  to={`/appointments/${appointmentId}`}
                  onClick={onClose}
                >
                  View appointment
                </Link>
              )}
              <Button onClick={onClose}>Done</Button>
            </>
          ) : (
            <div className="dialog-actions">
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => void decide("REJECT")}
              >
                Reject
              </Button>
              <Button disabled={busy} onClick={() => void decide("APPROVE")}>
                {busy
                  ? "Processing…"
                  : proposal.kind === "booking"
                    ? "Confirm booking"
                    : proposal.kind === "cancellation"
                      ? "Confirm cancellation"
                      : "Confirm reschedule"}
              </Button>
            </div>
          )}
          <Dialog.Close className="dialog-close" aria-label="Close">
            ×
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
