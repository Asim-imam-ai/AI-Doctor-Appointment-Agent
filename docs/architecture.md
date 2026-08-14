# AI Doctor Appointment Agent - System Architecture

> **Notice:** This project is an appointment assistance system and is NOT a medical diagnosis or treatment system.

## Architectural Layers

```
API Layer (FastAPI)
       ↓
LangGraph Agent Workflow (State Orchestration)
       ↓
Doctor Discovery Agent Node
       ↓
Doctor Search Tool (Read-Only Tool Boundary)
       ↓
Doctor Service (Business Logic)
       ↓
Doctor Repository (Data Abstraction)
       ↓
Supabase / PostgreSQL Database
```

Full Target Architecture:
```
API Layer (FastAPI)
       ↓
Guardrails Layer (Input/Output & Safety Checks)
       ↓
LangGraph Agent Workflow Layer (State Orchestration)
       ↓
Agent Nodes / Sub-agents
       ↓
Tool Execution Layer
       ↓
Service Layer (Business Logic)
       ↓
Repository Layer (Data Abstraction)
       ↓
Supabase / PostgreSQL Database
```

## Phase 3 — Doctor Discovery Agent Architecture

### 1. LangGraph State Workflow
- Graph State: `DoctorDiscoveryState` containing typed `messages`, `user_message`, `intent`, `search_criteria`, `tool_results`, `response`, `error`, and iteration/tool counters.
- Workflow Flow: `START` → `classify_intent` → (`agent` ↔ `tools`) → `END`.
- Intent Routing: Safely rejects medical advice/diagnosis (`OUT_OF_SCOPE`) and appointment mutation requests like booking/cancelling/rescheduling (`UNSUPPORTED`) before triggering LLM tool invocation.

### 2. Read-Only Tool Allowlist Boundary
- Tool Allowlist: `DOCTOR_DISCOVERY_TOOLS = [search_doctors_tool, get_doctor_details_tool]`.
- Strict Tool Safety: The agent does NOT have access to booking, cancellation, rescheduling, SQL execution, database mutation, email, or admin tools.

### 3. Data Access & Security Guarantees
1. **No Direct LLM Database Access:** The LLM does NOT access the database directly and cannot execute raw SQL or construct arbitrary database queries.
2. **Deterministic Data Retrieval:** Tools call `DoctorService` which routes through `DoctorRepository` to Supabase/PostgreSQL.
3. **Doctor Discovery is Read-Only:** Doctor discovery retrieves profile and specialty details. It does NOT claim appointment slot availability or confirm bookings.
4. **Appointment Availability in Phase 4:** Checking real-time slot availability is deferred to Phase 4.
5. **No Booking/Mutation:** Booking, rescheduling, and cancellation workflows are strictly prohibited in Phase 3.

## Phase 2 Data & Domain Layer Architecture

### 1. Database Schema (`supabase/migrations/001_initial_domain_schema.sql`)
The PostgreSQL database consists of 6 core domain tables:
- `patients`: Patient profiles indexed by `external_user_id` and `email`.
- `doctors`: Doctor profiles with `is_active` status and consultation durations.
- `specialties`: Medical specialties.
- `doctor_specialties`: Junction table establishing many-to-many doctor-specialty relationships.
- `doctor_availability`: Doctor available time slots with `status` (`AVAILABLE`, `BOOKED`, `BLOCKED`).
- `appointments`: Patient-doctor appointment records with controlled `status` (`PENDING`, `CONFIRMED`, `CANCELLED`, `RESCHEDULED`, `COMPLETED`, `NO_SHOW`, `EXPIRED`).

### 2. Database Constraints & Double-Booking Protection
- Timeorder checks: `start_time < end_time` enforced via database table constraints.
- Status enum checks: `status IN (...)` constraints prevent invalid status values.
- Double-booking prevention: PostgreSQL Exclusion constraint using `btree_gist` extension prevents overlapping appointment times (`tstzrange`) for the same doctor for non-cancelled/non-expired appointments (`PENDING` or `CONFIRMED`).

### 3. Timezone Strategy
- All timestamps (`start_time`, `end_time`, `created_at`, `updated_at`) are canonically stored with timezone awareness (`TIMESTAMPTZ` in PostgreSQL, timezone-aware `datetime` in Python models).
- Patient models track preferred timezone (default `UTC`).

### 4. Data Access & Security Boundaries
1. **LLM Isolation:** The LLM NEVER directly accesses the database or executes raw SQL queries.
2. **Authoritative State:** Database/service state is authoritative. Only a successful backend transaction establishes `CONFIRMED` appointment status.
3. **Supabase Security:** Service role keys remain strictly server-side. Application logic routes through repository abstractions.
4. **Test Database Strategy:** Repositories implement both `SupabaseRepository` (production/staging) and `InMemoryRepository` (deterministic testing/CI without external Supabase dependencies).

## Phase 7 — Appointment Reminders & Notifications Architecture

### 1. Deterministic Background Execution (No LLM in Loop)
- **Zero-LLM Responsibility:** The LLM is NEVER responsible for reminder eligibility, scheduled check intervals, checking appointment status, or directly executing notification dispatches. All reminder operations run via deterministic code (`ReminderService`, `NotificationService`).
- **Trigger Lifecycle:** Successful appointment booking (`atomic_create_appointment_and_update_slot`) automatically triggers 24-hour and 2-hour reminder generation.
- **Cascading Invalidation:** Appointment cancellation (`cancel_appointment`) or rescheduling (`atomic_reschedule_appointment`) immediately invalidates pending reminders (`CANCELLED` or re-computed schedules).

### 2. Provider Abstraction & Safe Delivery Pipeline
- **Notification Provider Interface:** Pluggable `NotificationProvider` interface with `MockNotificationProvider` for local testing/CI and email adapters.
- **Audit Trails & Retries:** Every notification attempt records a `NotificationDeliveryModel` entry (`SENDING`, `SENT`, `FAILED`). Failed dispatches feature bounded transient retries (max retries = 3).
- **Timezone Awareness & Preferences:** User notification preferences (`NotificationPreferenceModel`) govern channel toggles (Email, SMS, In-App) and user IANA timezones.

### 3. Worker Safety & Race Condition Protection
- **Idempotency Keys:** Unique idempotency keys (`appointment_id:reminder_type:scheduled_at`) prevent duplicate reminder schedules.
- **Atomic Claiming:** Multi-worker concurrency safety via atomic status transitions (`PENDING` → `PROCESSING`).
- **Revalidation Guardrails:** Prior to dispatch, reminders revalidate appointment existence, patient ownership, active status (`CONFIRMED`), and future time bounds. Stale/cancelled appointments transition to `SKIPPED`.

## Phase 8 — Advanced Guardrails, Safety & Secure Agent Boundaries

```text
Input
 ↓
Layer 1: Request Validation
 ↓
Layer 2: Input Size Limits
 ↓
Layer 3: Prompt Injection Defense
 ↓
Layer 4: Jailbreak Defense
 ↓
Layer 5: Medical Scope Boundary
 ↓
Layer 6: Authorization & Ownership
 ↓
Layer 7: Tool Allowlist & Policy
 ↓
Layer 8: Tool Input Sanitization
 ↓
Layer 9: Output Safety & Secret Protection
 ↓
Response
```

### 1. Deterministic Security Boundaries
- **Central Guardrail Engine (`app/guardrails/engine.py`):** Centralizes input size validation, regex-based prompt injection detection, jailbreak override detection, medical scope enforcement, and secret redaction.
- **Prompt Injection & Jailbreak Defense:** Rejects attempts to extract system prompts, bypass safety rules, or claim administrative elevation.
- **Medical Scope Boundary:** Redirects symptom diagnosis, prescription dosage, and treatment inquiries away from LLM execution to registered healthcare providers.
- **Strict Authorization:** Enforces deterministic resource ownership verification across patients and appointments. Raw client user IDs are never trusted without backend validation.

### 2. Output Redaction & Safe Failure
- **Secret Redaction:** `inspect_output_safety` dynamically scrubs API keys, bearer tokens, passwords, and database connection strings from LLM outputs.
- **No False Claims:** Output responses are validated against backend execution outcomes. The agent cannot claim booking/cancellation success unless confirmed by backend transactions.

## Phase 10 — Knowledge Base & RAG Architecture

```text
Approved Knowledge Files (docs/ & knowledge/)
       ↓
Ingestion Pipeline (File Validation, Hash, Normalization)
       ↓
Chunking (Semantic Splitting with Overlap)
       ↓
Embeddings Service (OpenAI text-embedding-3-small / Test Double)
       ↓
Vector Storage (Supabase pgvector / InMemory Storage)
       ↓
Retriever (Active Document & Category Filtering)
       ↓
Context Builder (Deduplicated Context Assembly)
       ↓
Grounded Answer Synthesis (LLM)
       ↓
Output Guardrail & Citation Verification
```

### 1. Controlled Knowledge & Version Management
- **Approved Ingestion Sources:** Only approved markdown/txt documents in `knowledge/` and `docs/` are ingested into `knowledge_documents` and `knowledge_chunks`. User inputs are treated strictly as untrusted query data.
- **Content Hashing & Version Deactivation:** SHA-256 content hashes prevent duplicate document ingestion. Ingesting an updated version automatically deactivates prior versions (`INACTIVE`), ensuring only `ACTIVE` documents enter the retrieval pipeline.

### 2. Vector Storage & Metadata Filtering
- **Supabase pgvector / In-Memory Vector Store:** Stores 1536-dimensional embeddings with HNSW cosine index (`hnsw (embedding vector_cosine_ops)`).
- **Metadata Filters:** Enforces strict deterministic filtering (`status = ACTIVE`, `category = APPOINTMENT_POLICY`) prior to top-k chunk context assembly.

### 3. Grounded Synthesis & Safety Boundaries
- **No-Context Fallback:** If retrieval similarity is below threshold or yields no results, the system explicitly returns `"I don't have enough information in the appointment knowledge base to answer that accurately."`
- **Prompt Injection Defense:** Retrieved chunks are injected into a dedicated context block marked as untrusted reference data, preventing embedded text instructions from overriding system guardrails.
- **Authoritative Operational Boundary:** RAG is never used to check live appointment states (booking, cancellation, slot availability). Operational queries route directly to authoritative database services.


