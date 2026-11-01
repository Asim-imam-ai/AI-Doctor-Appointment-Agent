# Agentic architecture refactor

## Original structure

Five workflow modules mixed node behavior and graph construction. Memory and RAG
were grouped with general services. Proposal tools owned mutation coordination
and proposal stores. The packaged entry point depended on a root module outside
the wheel. Repository splitting and a lockfile update were already uncommitted
when this task began and were preserved.

## Final boundaries

The directory tree in [architecture.md](architecture.md) documents the actual
layout. Public workflow imports delegate to `agents/graph`, whose graph builders
register functions from `agents/nodes`. State remains coherently grouped in
`agents/state.py`. Tools call domain services; repositories abstract persistence;
Supabase initialization remains under infrastructure. Guardrails and core remain
explicit shared layers. Memory and RAG have their own packages.

## Significant moves and extractions

| Original | Canonical location |
| --- | --- |
| `app/agents/<workflow>.py` graph functions | `app/agents/graph/<workflow>.py` |
| `app/agents/<workflow>.py` node functions | `app/agents/nodes/<workflow>.py` |
| `app/services/context_builder.py` | `app/memory/context_builder.py` |
| `app/services/conversation_service.py` | `app/memory/conversation_service.py` |
| `app/services/memory_service.py` | `app/memory/memory_service.py` |
| `app/services/summarizer.py` | `app/memory/summarizer.py` |
| `app/services/embeddings_service.py` | `app/rag/embeddings_service.py` |
| `app/services/ingestion_pipeline.py` | `app/rag/ingestion_pipeline.py` |
| `app/services/rag_service.py` | `app/rag/rag_service.py` |
| RAG result models in service | `app/schemas/knowledge.py` |
| Booking proposal helpers in tools | `app/services/booking_proposal.py` |
| Management proposal helpers in tools | `app/services/management_proposal.py` |
| Root `main.py` implementation | `app/main.py` |
| Repository monoliths (pre-existing split) | `app/repositories/in_memory/` and `supabase/` domain modules |

The five workflow names are `doctor_discovery`, `doctor_availability`,
`appointment_booking`, `appointment_cancellation`, and `appointment_rescheduling`.
No domain filenames were renamed merely for style. Deleted service paths are
moves listed above; deleted repository monolith paths are replaced by their
domain packages. No working feature was deleted.

New files are the ten graph/node modules, two proposal services, memory/RAG
package initializers and moved modules, repository packages from the existing
worktree split, and refactor documentation. `.dockerignore` excludes local
credentials, caches and environment files from image context. Existing workflow,
tool and root entrypoint compatibility imports retain one canonical implementation.

## Contracts and behavior

Node and graph function ASTs matched during extraction; proposal helper ASTs also
matched. HITL routing, approval gates, proposal versions, ownership checks and
revalidation remain in their original execution order. Existing guardrail code,
prompt wording, environment keys and migrations are retained. RAG and memory
implementations were moved with import changes. Existing tests were retained;
one lifespan regression test was added after startup exposed the missing
`LOG_LEVEL` setting. The setting now defaults to `INFO`, matching Compose.
Docker and Compose health checks use Python's standard library because curl is
installed only in the builder stage, not in the runtime image. Endpoint, interval,
service name and startup command remain unchanged.

Imports in API routes, nodes, services and tests point to the new memory/RAG
locations. Proposal nodes call services directly; tools retain compatibility
exports referencing the same stores. Existing domain/schema groupings remain
intact rather than being split into artificial packages.

## Validation and publication

See [architecture_validation.md](architecture_validation.md) for recorded evidence
and limitations. The final Python 3.12 run passed all 106 tests; Ruff lint,
formatting, application compilation and import checks passed. The Docker image
built successfully and passed its health check. `tzdata` was added as a runtime
dependency after Windows validation showed the standard library had no timezone
database. The branch is `refactor/agentic-architecture`; remote PR publication
is unavailable because the configured GitHub CLI token is invalid and no
GitHub MCP is connected.
