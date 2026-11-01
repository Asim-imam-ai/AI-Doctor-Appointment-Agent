type Props = {
  specialty: string;
  location: string;
  onSpecialtyChange: (value: string) => void;
  onLocationChange: (value: string) => void;
};

export function DoctorFilters({
  specialty,
  location,
  onSpecialtyChange,
  onLocationChange,
}: Props) {
  return (
    <div className="doctor-filters">
      <label>
        Specialty
        <input
          value={specialty}
          onChange={(event) => onSpecialtyChange(event.target.value)}
          placeholder="e.g. Cardiology"
        />
      </label>
      <label>
        Location
        <input
          value={location}
          onChange={(event) => onLocationChange(event.target.value)}
          placeholder="City or area"
        />
      </label>
    </div>
  );
}
