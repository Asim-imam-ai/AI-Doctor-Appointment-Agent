import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, test, vi } from "vitest";
import { AppointmentCard } from "../features/appointments/AppointmentPages";
import { DoctorCard } from "../features/doctors/DoctorPages";

vi.mock("../lib/services", () => ({
  doctors: {
    detail: vi.fn(async () => ({
      name: "Dr. Amira Khan",
      specialties: ["Cardiology"],
      location: "Karachi",
    })),
  },
  appointments: {},
  availability: {},
  approvals: {},
}));

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

  test("appointment card shows the returned doctor and links to the appointment", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
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
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Dr. Amira Khan")).toBeInTheDocument();
    expect(screen.getByText("CONFIRMED")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view details/i })).toHaveAttribute(
      "href",
      "/appointments/appointment-1",
    );
  });
});
