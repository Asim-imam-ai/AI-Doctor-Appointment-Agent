import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Clock3 } from "lucide-react";
import { availability } from "../../lib/services";
import { localToday, matchingSlots } from "../../lib/slots";
import {
  PageHeader,
  LoadingState,
  ErrorState,
  EmptyState,
  DateText,
} from "../../components/common";
import type { Slot } from "../../types/api";
const date = (value: string) => <DateText value={value} />;
export function AvailabilityPage() {
  const { doctorId } = useParams();
  const [day, setDay] = useState("");
  const [searchedDay, setSearchedDay] = useState("");
  const query = useQuery({
    queryKey: ["availability", doctorId, searchedDay],
    queryFn: ({ signal }) =>
      availability.searchForDoctor(doctorId!, searchedDay, signal),
    enabled: Boolean(doctorId && searchedDay),
  });
  const slots = matchingSlots(
    query.data?.slots ?? [],
    doctorId ?? "",
    searchedDay,
  );
  function submit(e: FormEvent) {
    e.preventDefault();
    if (!day) return;
    if (day === searchedDay) void query.refetch();
    else setSearchedDay(day);
  }
  return (
    <>
      <PageHeader
        eyebrow="CHOOSE A TIME"
        title="Available appointments"
        description="Select a date to view live appointment slots."
      />
      <form className="filter-card" onSubmit={submit}>
        <label>
          Appointment date
          <input
            type="date"
            value={day}
            min={localToday()}
            onChange={(e) => {
              setDay(e.target.value);
              setSearchedDay("");
            }}
            required
          />
        </label>
        <button className="button">Check availability</button>
      </form>
      {!searchedDay ? (
        <EmptyState>Choose a date to see available times.</EmptyState>
      ) : query.isLoading ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState
          message={(query.error as Error).message}
          retry={() => void query.refetch()}
        />
      ) : slots.length ? (
        <div className="slot-grid">
          {slots.map((s) => (
            <SlotCard key={s.id} slot={s} />
          ))}
        </div>
      ) : (
        <EmptyState>
          No slots were returned for this doctor and date. Try another date.
        </EmptyState>
      )}
    </>
  );
}
function SlotCard({
  slot,
  onSelect,
}: {
  slot: Slot;
  onSelect?: (slot: Slot) => void;
}) {
  const navigate = useNavigate();
  return (
    <article className="card slot-card">
      <Clock3 size={21} />
      <strong>{date(slot.start_time)}</strong>
      <span>{slot.doctor_name}</span>
      <button
        className="button secondary"
        onClick={() =>
          onSelect
            ? onSelect(slot)
            : navigate(`/book/${slot.doctor_id}/${slot.id}`, {
                state: { slot },
              })
        }
      >
        Select time
      </button>
    </article>
  );
}
