"""Add five more synthetic doctors and patients and six demo policies."""

from scripts import seed_demo_data as seed

seed.PREFIX = "ai-doctor-appointment-agent/demo/v2/"
seed.PATIENT_COUNT = 5
seed.CREATE_APPOINTMENTS = False
seed.PATIENT_NAME_PREFIX = "DEMO Batch 2 Patient"
seed.SOURCE_NAME = "demo_seed_v2.md"
seed.SPECIALISTS = [
    ("Batch 2 Family Medicine", "Fatima Noor"),
    ("Batch 2 Cardiology", "Usman Raza"),
    ("Batch 2 Dermatology", "Mariam Ali"),
    ("Batch 2 Pediatrics", "Bilal Shah"),
    ("Batch 2 Orthopedics", "Nadia Malik"),
]
seed.POLICIES = [
    (
        "CLINIC_INFORMATION",
        "Batch 2 clinic information",
        f"{seed.DEMO} DEMO Care Clinic is a fictional outpatient clinic. Example opening hours are Monday through Friday, 09:00 to 17:00 UTC. Emergency care is not provided.",
    ),
    (
        "APPOINTMENT_POLICY",
        "Batch 2 appointment policy",
        f"{seed.DEMO} Example appointments last 30 minutes. Please arrive 15 minutes early. The portal confirms an appointment only after approval succeeds.",
    ),
    (
        "BOOKING_POLICY",
        "Batch 2 booking policy",
        f"{seed.DEMO} Select a demo doctor and an available slot, then review and approve the booking proposal. Availability can change until the booking is confirmed.",
    ),
    (
        "CANCELLATION_POLICY",
        "Batch 2 cancellation policy",
        f"{seed.DEMO} Demo appointment cancellation requires an approved cancellation proposal. The demo backend normally requires at least 120 minutes before the appointment.",
    ),
    (
        "RESCHEDULING_POLICY",
        "Batch 2 rescheduling policy",
        f"{seed.DEMO} Select another available slot for the same demo doctor and approve the rescheduling proposal. Past appointments cannot be rescheduled.",
    ),
    (
        "FAQ",
        "Batch 2 clinic FAQ",
        f"{seed.DEMO} The demo portal supports doctor discovery, appointment availability, booking, cancellation and rescheduling. It does not provide medical advice or emergency services.",
    ),
]

if __name__ == "__main__":
    seed.main()
