import { useState, type FormEvent } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, MapPin, Search } from "lucide-react";
import { doctors } from "../../lib/services";
import {
  PageHeader,
  LoadingState,
  ErrorState,
  EmptyState,
} from "../../components/common";
import type { Doctor } from "../../types/api";
import { DoctorFilters } from "./DoctorFilters";
export function DoctorCard({ doctor }: { doctor: Doctor }) {
  return (
    <article className="card doctor-card">
      <div className="doctor-avatar">
        {doctor.name.split(" ").slice(-1)[0]?.charAt(0) ?? "D"}
      </div>
      <div>
        <span className="eyebrow">
          {doctor.specialties.join(" · ") || "Doctor"}
        </span>
        <h3>{doctor.name}</h3>
        <p>
          <MapPin size={15} />
          {doctor.location ?? doctor.clinic_name ?? "Location not listed"}
        </p>
      </div>
      <Link
        className="button secondary"
        to={`/doctors/${doctor.id}`}
        state={{ doctor }}
      >
        View profile <ArrowRight size={16} />
      </Link>
    </article>
  );
}
export function DoctorsPage() {
  const [input, setInput] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [location, setLocation] = useState("");
  const [term, setTerm] = useState("");
  const search = useQuery({
    queryKey: ["doctors", term],
    queryFn: ({ signal }) => doctors.search(term, signal),
    enabled: Boolean(term),
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    const query = [
      input.trim(),
      specialty.trim() && `specialty ${specialty.trim()}`,
      location.trim() && `in ${location.trim()}`,
    ]
      .filter(Boolean)
      .join(" ");
    if (query) setTerm(query);
  }
  return (
    <>
      <PageHeader
        eyebrow="FIND THE RIGHT FIT"
        title="Find a doctor"
        description="Search by doctor name, specialty, clinic, or location."
      />
      <form className="search-bar" onSubmit={submit}>
        <Search size={21} />
        <input
          aria-label="Search doctors"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Try ‘cardiologist in Karachi’"
        />
        <button className="button">Search</button>
      </form>
      <DoctorFilters
        specialty={specialty}
        location={location}
        onSpecialtyChange={setSpecialty}
        onLocationChange={setLocation}
      />
      {!term ? (
        <EmptyState>
          Enter a specialty, doctor name, or location to search the live doctor
          directory.
        </EmptyState>
      ) : search.isLoading ? (
        <LoadingState />
      ) : search.isError ? (
        <ErrorState
          message={(search.error as Error).message}
          retry={() => void search.refetch()}
        />
      ) : (
        <>
          <div className="section-heading">
            <h2>Search results</h2>
            <span>{search.data?.doctors.length ?? 0} doctors</span>
          </div>
          {search.data?.doctors.length ? (
            <div className="card-grid">
              {search.data.doctors.map((d) => (
                <DoctorCard key={d.id} doctor={d} />
              ))}
            </div>
          ) : (
            <EmptyState>
              No doctors matched your search. Try a different term.
            </EmptyState>
          )}
        </>
      )}
    </>
  );
}
export function DoctorDetails() {
  const { id } = useParams();
  const state = useLocation().state as { doctor?: Doctor } | null;
  const candidate = state?.doctor;
  const doctor = candidate?.id === id ? candidate : null;
  return (
    <>
      <Link className="back-link" to="/doctors">
        ← Back to doctors
      </Link>
      {!doctor ? (
        <EmptyState>
          This doctor profile is not available from a direct link. Search the
          doctor directory to open a current listing.
        </EmptyState>
      ) : (
        <>
          <div className="profile-hero">
            <div className="doctor-avatar large">
              {doctor.name.split(" ").slice(-1)[0]?.charAt(0)}
            </div>
            <div>
              <span className="eyebrow">{doctor.specialties.join(" · ")}</span>
              <h1>{doctor.name}</h1>
              <p>
                {doctor.clinic_name ?? "Clinic not listed"}{" "}
                {doctor.location && `· ${doctor.location}`}
              </p>
            </div>
          </div>
          <div className="card details-card">
            <h2>About this doctor</h2>
            <p>{doctor.bio ?? "No biography is available."}</p>
            <p>Typical consultation: {doctor.consultation_duration} minutes</p>
            <Link className="button" to={`/availability/${doctor.id}`}>
              See available times <ArrowRight size={17} />
            </Link>
          </div>
        </>
      )}
    </>
  );
}
