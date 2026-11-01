import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";
import { AppointmentCard } from "../features/appointments/AppointmentPages";
import { DoctorCard } from "../features/doctors/DoctorPages";

describe("patient result cards", () => {
  test("doctor card shows fields returned by the discovery API", () => {
    render(
      <MemoryRouter>
        <DoctorCard
          doctor={{
            id: "doctor-1",
            name: "Dr. Amira Khan",
            specialties: ["Cardiology"],
            clinic_name: "Central Clinic",
            location: "Karachi",
            bio: null,
            consultation_duration: 30,
            is_active: true,
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("Dr. Amira Khan")).toBeInTheDocument();
    expect(screen.getByText("Karachi")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view profile/i })).toHaveAttribute(
      "href",
      "/doctors/doctor-1",
    );
  });

  test("appointment card links to the authoritative appointment detail", () => {
    render(
      <MemoryRouter>
        <AppointmentCard
          appointment={{
            id: "appointment-1",
            doctor_id: "doctor-1",
            patient_id: "patient-1",
            start_time: "2026-11-05T10:00:00Z",
            end_time: "2026-11-05T10:30:00Z",
            status: "CONFIRMED",
            reason: null,
            created_at: "2026-11-01T10:00:00Z",
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("CONFIRMED")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view details/i })).toHaveAttribute(
      "href",
      "/appointments/appointment-1",
    );
  });
});
