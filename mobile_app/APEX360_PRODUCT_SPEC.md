# Apex360 — evidence-informed student coaching product specification

Status: approved product direction, NOT implemented features. Student-first Flutter app + Telegram bot + counselor dashboard. No production schema or student records should be modified from this specification alone.

## Design principles
1. Coach-guided self-regulated learning: Plan → Do → Monitor → Reflect → Adjust.
2. Support retrieval practice, spaced review and interleaving *in the context of each subject*; do not equate study hours with learning.
3. Compassionate feedback: compare students with their own baseline; avoid shame, streak penalties, diagnostic labels, or unvalidated mental-health inferences.
4. AI proposes summaries and next steps; the licensed counselor reviews consequential decisions.
5. Offline-first event capture with explicit sync status; preserve all existing student records.
6. Privacy by design for minors: student, counselor, parent and admin roles with least-privilege access; parental visibility configured transparently, sensitive wellbeing notes not shared by default.

## MVP priority 1 — student workflow
- Study activity: UUID, student_id (server-derived), client_created_at, timezone, subject, activity_type (study/practice/review/video), started_at, ended_at, duration_minutes, timer_or_manual, optional notes, device_id, sync_state.
- Offline queue: local encrypted database where feasible, unique event IDs and idempotent server POST; append-only events with correction history rather than overwrite.
- Daily plan: per-task goal, planned minutes, completed minutes, status, source counselor/student, revision timestamp.
- Daily reflection: effort, perceived focus, obstacle and one next step. Mood/stress/sleep optional, separate consent and restricted permissions.
- Student home: personalized greeting, today plan, start timer, one-tap activity capture, daily summary, clear offline indicator. No fabricated demo achievements.
- Learning quality: retrieval questions, spaced-review reminders, test error types (knowledge, recall, misunderstanding, time, attention), calibrated confidence.

## MVP priority 2 — coaching dashboard
- Review queue with configurable rules: missed check-ins, sustained plan mismatch, unanswered counselor message; rules are operational prompts, NOT diagnosis.
- Counselor notes, agreed actions, follow-up due date, parent-contact log, intervention outcome.
- Weekly student report: planned/completed, learning activity mix, tests and corrections, adherence trend, self-reported obstacles, next-week commitments.
- Show data provenance (manual vs timer vs inferred) and missing data. Never assume missing data means zero studying.

## MVP priority 3 — parent and bot
- Parent: scoped progress and agreed support actions, no raw private counseling or mood notes by default.
- Telegram bot: quick daily check-in, reminder, counselor follow-up and summary; app remains the richer offline interface.
- No unrestricted group rankings, addictive gamification, or push notifications at night.

## Architecture and security acceptance
- Keep current Railway production on main and persistent SQLite volume untouched during feature development.
- New schema only via additive, reversible, tested migrations; back up before production migration.
- Every endpoint authorizes by authenticated server-side student identity; do not trust student_id supplied by client.
- Audit counselor/parent access; consent version, retention/deletion policy, export controls.
- Offline conflict handling: immutable activity event IDs, idempotent upsert, server-generated sync receipt; resolve edits explicitly.
- Minimum tests: auth expiry, replay and revocation; student isolation; offline duplicate sync; timezone/date rollover; partial network failure; migration against existing data snapshot.
- Pilot with small consenting cohort; assess daily logging burden, weekly retention, counselor workload and student-reported usefulness before scaling.

## Phased delivery
1. Validate auth and real profile; add logout and session revocation, tests.
2. Local offline activity timer and daily log with a clear unsynced state.
3. Idempotent authenticated sync API and minimal reports.
4. Counselor queue and actionable weekly review.
5. Retrieval/spaced-review recommendations and parent view after access/consent checks.
6. Evaluate against a pilot baseline; adjust based on measured results.

## Evidence
- EEF (2025) Metacognition and Self-Regulated Learning guidance: https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/metacognition
- Carpenter, Pan & Butler (2022), Nature Reviews Psychology: https://www.nature.com/articles/s44159-022-00089-1
- Ruitenburg et al. (2026), classroom meta-analysis: https://link.springer.com/article/10.1007/s10648-026-10225-5

Note: The Darsita screenshots provided by the user are design references (activity timer, daily timeline, report cards), not a verified specification of that service. We borrow workflow ideas, not its visual identity or proprietary implementation.
