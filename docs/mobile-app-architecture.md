# Taranom Hamdeli mobile app architecture

## Product decision

Build one Flutter application for Android and iOS. The first usable release is
student-first, while the identity and authorization model reserves separate
roles for parents, counselors, and center administrators.

The existing Telegram bot, FastAPI web panels, SQLite database, and Railway
persistent volume remain in service. The mobile app is an additional client,
not a replacement. No existing student records are migrated or deleted.

## Current backend baseline

- FastAPI application is assembled in `app/admin.py`.
- Telegram bot runs alongside Uvicorn from `app/main.py`.
- Existing database helpers and schema live in `app/db.py` and
  `app/migrations.py`.
- SQLite database is configured by `DATABASE_PATH` and currently resides on
  the persistent Railway volume.
- Existing student identity is linked to a Telegram numeric user ID.

## Mobile client

- Flutter, with Android and iOS targets.
- RTL-first Persian interface and accessible typography.
- Local SQLite storage (Drift) for cached plans, downloaded tests, draft
  answers, daily reports, and mood check-ins.
- An outbox stores user actions with client-generated UUIDs.
- Each action is retried safely after reconnect; the server must enforce
  idempotency to prevent duplicate reports or assessment attempts.
- The app displays pending, synced, and failed items and never silently drops
  offline entries.

## Backend boundaries

The app must communicate only through versioned HTTPS endpoints under
`/api/v1/mobile`; it must never connect directly to the SQLite database.

The first foundation endpoints are:
- `GET /api/v1/mobile/health`: connectivity check.
- `GET /api/v1/mobile/capabilities`: supported roles, offline features, and
  sync contract.

No personal-data endpoint is exposed in this foundation change. Before adding
those endpoints, implement account verification through the existing Telegram
bot, short-lived access tokens, refresh-token rotation, role checks, rate
limits, and audit logging. Do not use a Telegram ID or phone number alone as
a password.

## Sync contract

Every queued operation will include:
- `operation_id`: client-generated UUID, unique across retries.
- `operation_type`: e.g. `daily_report.submit` or `assessment.answer`.
- `entity_id`: optional server-side record ID.
- `client_created_at`: timestamp with timezone.
- `payload`: validated operation data.

The server records processed operation IDs and returns the canonical server
record plus sync status. Replaying an operation ID returns the original result
instead of creating a duplicate. Conflicting edits must be returned explicitly
for reconciliation; last-write-wins must not silently overwrite counselor
plans or sensitive assessment records.

## Delivery phases

1. Backend contract and safe authentication.
2. Student Flutter shell, registration/activation, profile, and dashboard.
3. Offline plan cache, daily report, local queue, and sync.
4. Downloadable assessments and offline answer capture.
5. Parent, counselor, and admin roles and screens.
6. Notifications, security review, device testing, and store distribution.

## Privacy and safety

- Enforce ownership and role permissions server-side on every request.
- Store only the minimum local data needed for offline use.
- Encrypt sensitive local data and clear protected caches on logout where
  appropriate.
- Keep psychological assessment details behind explicit permissions.
- Use HTTPS, secure token storage, backups, and audit logs.
- Do not expose AI provider keys or database credentials in the mobile app.
