# CarePath patient frontend

React, TypeScript, Vite and Tailwind patient portal for the FastAPI doctor appointment agent.

## Local setup

Copy `.env.example` to `.env` and set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` to browser-safe Supabase values. The Vite development server proxies `/api` to FastAPI on port 8000. Start the backend first, then run:

```powershell
npm install
npm run dev
```

Use `npm run build`, `npm run lint`, and `npm run test` for validation. Run `npm run test:e2e` with an installed Chrome browser for controlled browser tests. These Playwright tests intercept API responses and do not write patient records. The API base defaults to the current origin. Set `VITE_API_BASE_URL` only when the backend is hosted at another origin and that backend allows the frontend origin.

## Patient routes

`/` is the public landing page. `/login`, `/register`, `/forgot-password`, and `/auth/callback` handle account access. An authenticated account without a linked patient record goes to `/onboarding` before entering the portal. Patient pages are `/dashboard`, `/doctors`, `/doctors/:id`, `/availability/:doctorId`, `/book/:doctorId/:slotId`, `/appointments`, `/appointments/:id`, `/chat`, `/knowledge`, and `/profile`.

## Backend connections

| Screen | Backend operation |
| --- | --- |
| Doctor search | `POST /api/v1/doctors/search` |
| Availability | `POST /api/v1/availability/search` |
| Dashboard and appointment history | `GET /api/v1/appointments` |
| Appointment details | `GET /api/v1/appointments/{id}` |
| Booking | `POST /api/v1/appointments/prepare`, then `POST /api/v1/appointments/{proposal_id}/approve` |
| Cancellation | `POST /api/v1/appointments/cancel/prepare`, then `POST /api/v1/appointments/cancel/{proposal_id}/approve` |
| Rescheduling | `POST /api/v1/appointments/reschedule/prepare`, then `POST /api/v1/appointments/reschedule/{proposal_id}/approve` |
| Chat and history | `POST /api/v1/chat`, `GET/POST /api/v1/conversations`, `GET /api/v1/conversations/{id}` |
| Clinic guide | `POST /api/v1/knowledge/search` |
| Preferences | `GET/POST /api/v1/conversations/memory`, `DELETE /api/v1/conversations/memory/{id}` |
| Patient setup and profile | `POST /api/v1/patients/me`, `GET /api/v1/patients/me` |

Authenticated requests attach the Supabase access token. The backend resolves the patient from the token. Appointment changes only appear confirmed after the approval response reports `BOOKED`; the appointment list is refreshed after each decision.

## Current backend limitations

- After Supabase registration and email confirmation, a new user completes the patient setup form. Accounts whose email already belongs to a separate unlinked patient record need clinic support to link that record.
- The backend has no doctor detail endpoint. A doctor profile opens from the current search result; a direct reload requires searching again.
- Chat returns text, intent, and a HITL flag, but no structured doctor/slot/proposal payload or streaming endpoint. The chat screen therefore shows plain assistant text and does not invent workflow cards or progress events.
- The backend supports reading the current patient's name, email, phone, and timezone, but has no profile update endpoint. The profile screen shows the linked record and supports the backend's specialty, doctor, time range, and timezone preferences.
- Live Supabase and OpenAI credentials plus an isolated test project are needed for end-to-end validation against the real services. The checked-in Playwright suite verifies browser interactions with controlled responses; it does not prove hosted database mutation or LLM behavior.
