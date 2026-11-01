import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { DoctorFilters } from "./DoctorFilters";

test("doctor filters send the selected specialty and location to search state", () => {
  const specialty = vi.fn();
  const location = vi.fn();
  render(
    <DoctorFilters
      specialty=""
      location=""
      onSpecialtyChange={specialty}
      onLocationChange={location}
    />,
  );
  fireEvent.change(screen.getByLabelText("Specialty"), {
    target: { value: "Cardiology" },
  });
  fireEvent.change(screen.getByLabelText("Location"), {
    target: { value: "Karachi" },
  });
  expect(specialty).toHaveBeenCalledWith("Cardiology");
  expect(location).toHaveBeenCalledWith("Karachi");
});
