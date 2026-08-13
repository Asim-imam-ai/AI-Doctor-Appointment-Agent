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
