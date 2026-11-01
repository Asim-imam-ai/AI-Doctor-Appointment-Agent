# Refactor validation record

The working baseline included an uncommitted repository split and lockfile
update. These are preserved as user work. Comparing repository methods with
`71ec2ff` found pre-existing local-variable renames, type annotations, superclass
initialization, memory parameter renames (`memory` to `item`), knowledge model
serialization changes, and RPC fallback logging. These are not evidence of
behavior changes introduced by the graph/memory/tool extraction.

The five workflow extractions were checked by comparing Python ASTs for every
function, including nested routing functions. All matched before import cleanup.
The nine proposal service functions were checked the same way. Proposal tool
compatibility exports reference the canonical service functions and stores.

Completed checks:

- Baseline tests: 105 passed, zero failures/skips.
- After graph extraction: 105 passed, zero failures/skips.
- After memory/RAG and proposal extraction: 105 passed, zero failures/skips.
- After schema relocation and startup fix: 106 passed, zero failures/skips,
  including the new lifespan and entrypoint-identity regression test. A final
  run in the project Python 3.12 environment also passed all 106 tests. The
  final run disabled local `.env` loading in-process to avoid contacting the
  configured Supabase service, and redirected pytest temporary files into the
  workspace because the sandbox denies the default Windows temp directory.
- The final Windows run exposed that `zoneinfo` has no bundled timezone database
  on Windows. `tzdata` is now an explicit runtime dependency so timezone names
  also work on Windows and minimal Linux images.
- Repository-wide Ruff lint and format checks passed (142 files formatted).
- Application compilation passed.
- No old memory/RAG service imports found in application, tests or documentation.
- No database migration changes.
- GitHub default branch confirmed as `main` through CLI; MCP unavailable.

Four unit tests only assert `True` and are not meaningful coverage. Live
Supabase behavior is not proven by the in-memory tests.

The corrected explicit import-graph scan resolved 114 modules with no missing
modules or cycles, resolving package child imports separately. All application
modules imported successfully; a TestClient lifespan startup, health request and
shutdown passed. This establishes import/runtime startup behavior independently
of the static scan.

Container inspection found that the existing health check depended on curl,
which was installed only in the builder stage. Dockerfile and Compose now use
the runtime's Python standard library for the same health endpoint. Pytest temp
files are excluded from Docker context because the sandbox denies access to
their Windows temp path.

The Docker image built successfully as `doctor-appointment-agent:architecture`.
Its `/api/v1/health` endpoint returned `{"status":"ok","service":"doctor-appointment-agent"}`
and the configured health check reached `healthy`. The temporary validation
container was stopped and removed.
