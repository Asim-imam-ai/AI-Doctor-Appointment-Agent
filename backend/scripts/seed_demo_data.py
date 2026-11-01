"""Insert clearly marked demo records without replacing existing clinic data.

Run from the repository root with: uv run --directory backend python -m scripts.seed_demo_data
The configured Supabase project and Voyage account will be used.
"""

import hashlib
import uuid
from datetime import datetime, time, timedelta, timezone

from app.infrastructure.db.supabase import get_supabase_client
from app.knowledge.embeddings import EmbeddingsService
from app.knowledge.ingestion import IngestionPipeline

PREFIX = "ai-doctor-appointment-agent/demo/v1/"
DEMO = "DEMO ONLY: This is fictional test data, not a real clinic policy."
PATIENT_COUNT = 2
CREATE_APPOINTMENTS = True
PATIENT_NAME_PREFIX = "DEMO Patient"
SOURCE_NAME = "demo_seed_v1.md"

SPECIALISTS = [
    ("General Practice", "Ayesha Khan"),
    ("Cardiology", "Omar Malik"),
    ("Dermatology", "Sara Ahmed"),
    ("Pediatrics", "Ali Hassan"),
]

POLICIES = [
    (
        "CLINIC_INFORMATION",
        "Clinic information",
        f"{DEMO} Demo Care Clinic is a fictional outpatient clinic. Example hours are Monday through Friday, 09:00 to 17:00 UTC. This demo clinic does not provide emergency services.",
    ),
    (
        "APPOINTMENT_POLICY",
        "Appointment policy",
        f"{DEMO} Demo appointments are 30 minutes long. Please arrive 15 minutes before an appointment. Appointments are subject to availability and confirmation in the portal.",
    ),
    (
        "BOOKING_POLICY",
        "Booking policy",
        f"{DEMO} To book, choose a demo doctor and an available time, review the proposal, and approve it. A request is confirmed only after the portal reports a successful booking.",
    ),
    (
        "CANCELLATION_POLICY",
        "Cancellation policy",
        f"{DEMO} Demo appointments can be cancelled through the portal after reviewing and approving a cancellation proposal. The demo backend normally requires at least 120 minutes before the appointment.",
    ),
    (
        "RESCHEDULING_POLICY",
        "Rescheduling policy",
        f"{DEMO} To reschedule, choose another available slot for the same demo doctor, review the change, and approve the proposal. Past appointments cannot be rescheduled.",
    ),
    (
        "FAQ",
        "Clinic FAQ",
        f"{DEMO} The demo portal can help find a doctor, check availability, and manage appointments. It does not provide diagnosis, treatment, medication advice, or emergency care.",
    ),
]


def demo_id(label: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, PREFIX + label))


def one(client, table: str, record_id: str, columns: str = "*"):
    result = client.table(table).select(columns).eq("id", record_id).limit(1).execute()
    return (result.data or [None])[0]


def insert_once(client, table: str, payload: dict, identity_field: str) -> bool:
    old = one(client, table, payload["id"], f"id,{identity_field}")
    if old:
        if old.get(identity_field) != payload[identity_field]:
            raise RuntimeError(f"Refusing to replace a non-demo {table} record")
        return False
    client.table(table).insert(payload).execute()
    return True


def main() -> None:
    client = get_supabase_client()
    embeddings = EmbeddingsService()
    chunks_by_policy = [
        IngestionPipeline.chunk_text(content) for _, _, content in POLICIES
    ]
    all_chunks = [chunk for chunks in chunks_by_policy for chunk in chunks]
    # Generate all vectors before writing any data, so provider errors do not
    # leave partially created demo policy documents.
    vectors = iter(embeddings.embed_batch(all_chunks, input_type="document"))
    generated = [[next(vectors) for _ in chunks] for chunks in chunks_by_policy]
    counts = {
        "specialties": 0,
        "doctors": 0,
        "slots": 0,
        "patients": 0,
        "appointments": 0,
        "policies": 0,
        "chunks": 0,
    }
    warnings = []

    slots_by_doctor = []
    for specialty, name in SPECIALISTS:
        specialty_id = demo_id("specialty/" + specialty)
        doctor_id = demo_id("doctor/" + name)
        counts["specialties"] += insert_once(
            client,
            "specialties",
            {
                "id": specialty_id,
                "name": "DEMO - " + specialty,
                "description": "Fictional specialty for testing.",
                "is_active": True,
            },
            "name",
        )
        counts["doctors"] += insert_once(
            client,
            "doctors",
            {
                "id": doctor_id,
                "name": "Dr. DEMO " + name,
                "bio": "Fictional provider for testing only.",
                "clinic_name": "DEMO Care Clinic",
                "location": "Demo City",
                "consultation_duration": 30,
                "is_active": True,
            },
            "name",
        )
        relation = (
            client.table("doctor_specialties")
            .select("doctor_id")
            .eq("doctor_id", doctor_id)
            .eq("specialty_id", specialty_id)
            .limit(1)
            .execute()
        )
        if not relation.data:
            client.table("doctor_specialties").insert(
                {"doctor_id": doctor_id, "specialty_id": specialty_id}
            ).execute()
        doctor_slots = []
        for offset in range(1, 15):
            day = datetime.now(timezone.utc).date() + timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            for hour in (9, 15):
                start = datetime.combine(day, time(hour=hour), tzinfo=timezone.utc)
                slot_id = demo_id(f"slot/{doctor_id}/{start.isoformat()}")
                payload = {
                    "id": slot_id,
                    "doctor_id": doctor_id,
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(minutes=30)).isoformat(),
                    "status": "AVAILABLE",
                }
                counts["slots"] += insert_once(
                    client, "doctor_availability", payload, "doctor_id"
                )
                doctor_slots.append(slot_id)
        slots_by_doctor.append((doctor_id, doctor_slots))

    for number in range(1, PATIENT_COUNT + 1):
        patient_id = demo_id(f"patient/{number}")
        email = f"demo-{patient_id}@example.invalid"
        counts["patients"] += insert_once(
            client,
            "patients",
            {
                "id": patient_id,
                "name": f"{PATIENT_NAME_PREFIX} {number}",
                "email": email,
                "timezone": "UTC",
            },
            "email",
        )
        if not CREATE_APPOINTMENTS:
            continue
        doctor_id, doctor_slots = slots_by_doctor[number - 1]
        slot_id = doctor_slots[0]
        existing = (
            client.table("appointments")
            .select("id")
            .eq("patient_id", patient_id)
            .eq("reason", "DEMO appointment for testing only")
            .eq("status", "CONFIRMED")
            .limit(1)
            .execute()
        )
        if not existing.data:
            try:
                client.rpc(
                    "book_appointment_slot",
                    {
                        "p_patient_id": patient_id,
                        "p_doctor_id": doctor_id,
                        "p_slot_id": slot_id,
                        "p_reason": "DEMO appointment for testing only",
                    },
                ).execute()
                counts["appointments"] += 1
            except Exception as exc:
                warnings.append(
                    f"Demo appointment {number} not created ({type(exc).__name__}, code {getattr(exc, 'code', None)})"
                )

    for (category, title, content), chunks, chunk_vectors in zip(
        POLICIES, chunks_by_policy, generated, strict=True
    ):
        doc_id = demo_id("policy/" + category)
        doc_title = "[DEMO] " + title
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        old = one(
            client,
            "knowledge_documents",
            doc_id,
            "id,title,content_hash,status,metadata",
        )
        if old and (old["title"] != doc_title or old["content_hash"] != content_hash):
            raise RuntimeError("Refusing to replace an existing knowledge document")
        if not old:
            client.table("knowledge_documents").insert(
                {
                    "id": doc_id,
                    "title": doc_title,
                    "category": category,
                    "version": "1.0",
                    "status": "INACTIVE",
                    "source": SOURCE_NAME,
                    "content_hash": content_hash,
                    "metadata": {"demo": True, "seed_pending": True},
                }
            ).execute()
            counts["policies"] += 1
        for index, (chunk, vector) in enumerate(
            zip(chunks, chunk_vectors, strict=True)
        ):
            chunk_id = demo_id(f"chunk/{category}/{index}")
            prior = one(client, "knowledge_chunks", chunk_id, "id,document_id,content")
            if prior:
                if prior["document_id"] != doc_id or prior["content"] != chunk:
                    raise RuntimeError(
                        "Refusing to replace an existing knowledge chunk"
                    )
                continue
            client.table("knowledge_chunks").insert(
                {
                    "id": chunk_id,
                    "document_id": doc_id,
                    "chunk_index": index,
                    "content": chunk,
                    "embedding": vector,
                    "metadata": {
                        "demo": True,
                        "title": doc_title,
                        "category": category,
                        "version": "1.0",
                        "source": SOURCE_NAME,
                    },
                }
            ).execute()
            counts["chunks"] += 1
        if not old or (
            old["status"] == "INACTIVE"
            and (old.get("metadata") or {}).get("seed_pending") is True
        ):
            client.table("knowledge_documents").update(
                {"status": "ACTIVE", "metadata": {"demo": True}}
            ).eq("id", doc_id).execute()

    print("Demo records inserted:", counts)
    for warning in warnings:
        print(warning)
    query_vector = embeddings.embed_text(
        "DEMO cancellation policy 120 minutes", input_type="query"
    )
    matches = (
        client.rpc(
            "match_knowledge_chunks",
            {
                "query_embedding": query_vector,
                "match_count": 50,
                "filter_category": "CANCELLATION_POLICY",
            },
        )
        .execute()
        .data
        or []
    )
    print(
        "Demo cancellation policy retrieved:",
        any(
            str(row.get("document_id")) == demo_id("policy/CANCELLATION_POLICY")
            for row in matches
        ),
    )


if __name__ == "__main__":
    main()
