# AI Doctor Appointment Agent - System Architecture

> **Notice:** This project is an appointment assistance system and is NOT a medical diagnosis or treatment system.

## Architectural Layers

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

## Data Access & Security Boundaries

1. **LLM Isolation:** The LLM NEVER directly accesses the database or executes raw SQL queries.
2. **Authoritative State:** Database/service state is authoritative. The LLM must not hallucinate availability, bookings, or cancellations.
3. **Human-In-The-Loop (HITL):** Sensitive state mutations (booking, rescheduling, cancelling) require HITL approval before execution.
4. **Guardrail Enforcements:** Prompt injection protection, jailbreak detection, emergency detection, and healthcare scope enforcement operate as independent security boundaries around agent execution nodes.
