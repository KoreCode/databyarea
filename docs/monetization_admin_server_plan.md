# Monetization + Script-Runner Server + Admin Page Implementation Plan

## 1) Goals

1. Build a safe internal server that can run existing data-generation scripts in controlled jobs.
2. Provide an authenticated admin page for operators to trigger jobs, monitor status, and review logs.
3. Introduce monetization features without disrupting organic SEO traffic.
4. Establish a phased rollout that prioritizes security, observability, and recoverability.

## 2) Scope

### In scope
- Backend API service for job orchestration.
- Job queue and worker process to execute repository scripts.
- Admin web UI for run/monitor/cancel/retry workflows.
- Monetization foundation (sponsorship blocks, lead forms, premium/API data path).
- Auditing, auth, and operational dashboards.

### Out of scope (phase 1)
- Full user-facing SaaS account system.
- Billing automation beyond a small pilot.
- Rewriting legacy script logic.

## 3) Current-State Assumptions

- Repository contains script entry points under `scripts/` and data artifacts under `data/`.
- Site is largely static and generated from scripts.
- Job execution is likely local/manual today.

## 4) Target Architecture

## 4.1 Components

1. **API Server** (FastAPI or Express):
   - Exposes endpoints for auth, job CRUD, script catalog, run history, and logs.
   - Writes job metadata to Postgres.

2. **Worker Service**:
   - Pulls queued jobs.
   - Spawns script processes using allowlisted commands only.
   - Streams stdout/stderr logs to storage.

3. **Queue Layer**:
   - Redis + RQ/Celery/BullMQ for async jobs and retries.

4. **Admin UI**:
   - Auth-protected dashboard.
   - Pages: Jobs, Scripts, Schedules, Logs, Monetization settings.

5. **Storage**:
   - Postgres for entities (jobs, scripts, users, audits).
   - Object storage (or filesystem in MVP) for job artifacts/log bundles.

6. **Observability**:
   - Structured logs, metrics, error tracking, alerting.

## 4.2 Data Model (MVP)

- `users` (id, email, role, last_login_at)
- `scripts` (id, key, command, timeout_sec, enabled)
- `jobs` (id, script_id, status, started_at, finished_at, trigger_type, triggered_by)
- `job_logs` (id, job_id, stream, ts, line)
- `schedules` (id, script_id, cron, enabled)
- `audit_events` (id, actor_user_id, action, target_type, target_id, ts, metadata)

## 4.3 Security Guardrails

- Role-based access: `admin`, `operator`, `viewer`.
- SSO or strong password + TOTP in phase 1.
- Script execution allowlist (no arbitrary shell input from UI).
- Per-script timeout and memory limits.
- Network egress restriction for workers where possible.
- Immutable audit log for privileged operations.

## 5) API Surface (MVP)

- `POST /auth/login`
- `POST /auth/logout`
- `GET /scripts`
- `POST /jobs` (script key + params)
- `GET /jobs`
- `GET /jobs/{id}`
- `POST /jobs/{id}/cancel`
- `POST /jobs/{id}/retry`
- `GET /jobs/{id}/logs`
- `GET/POST /schedules`

## 6) Admin Page UX (MVP)

### 6.1 Pages

1. **Dashboard**
   - Last 24h success/failure rate.
   - Queue depth.
   - Last publish time.

2. **Run Script**
   - Select allowlisted script.
   - Optional parameter form (strict schema).
   - Dry-run toggle.

3. **Jobs**
   - Filter by status/date/script.
   - View live logs.
   - Retry/cancel actions.

4. **Schedules**
   - Cron entries with enable/disable.
   - Next run preview.

5. **Monetization Settings**
   - Affiliate block toggles by content type.
   - Lead-form routing destinations.
   - Experiments and variant assignment.

## 7) Monetization Strategy

## 7.1 Revenue Streams

1. **Affiliate modules** on high-intent pages (home services, utilities, insurance).
2. **Lead generation forms** with geo-specific routing.
3. **Sponsored placement slots** (clearly labeled).
4. **Premium data/API** for agencies and local businesses.

## 7.2 Placement Rules

- Keep informational content first; monetize below trust-building sections.
- Max 1–2 monetization units above fold.
- Add clear disclosures and FTC-compliant language.
- Exclude YMYL-style pages from aggressive monetization until quality checks pass.

## 7.3 Experimentation

- A/B test module format and position.
- Core KPI set:
  - Revenue per 1,000 sessions (RPM)
  - Lead conversion rate
  - Bounce rate / engaged sessions
  - Organic rankings for top pages

## 8) Delivery Roadmap

## Phase 0 (Week 1): Discovery + hardening
- Inventory scripts and define script registry schema.
- Classify scripts by runtime, dependencies, and criticality.
- Define success/error taxonomy.

## Phase 1 (Weeks 2–3): Backend MVP
- Stand up API service + Postgres + Redis.
- Implement auth, scripts list, create job, job status, log streaming.
- Worker executes allowlisted scripts with timeout/retry.

## Phase 2 (Weeks 4–5): Admin UI MVP
- Implement dashboard, run-script form, jobs table, log panel.
- Add role checks and audit trail views.

## Phase 3 (Week 6): Scheduling + operations
- Cron scheduling UI + backend.
- Alerting (job failure, queue stuck, runtime spikes).
- Backfill runbook for common incidents.

## Phase 4 (Weeks 7–8): Monetization pilot
- Ship affiliate and lead modules on 5–10 page templates.
- Add experiments and reporting pipeline.
- Review SEO impact before wider rollout.

## 9) Technical Decisions to Finalize

1. **Runtime stack**: Python/FastAPI + Celery vs Node/Express + BullMQ.
2. **Deployment target**: single VPS vs container platform (Fly/Render/AWS ECS).
3. **Auth provider**: managed (Clerk/Auth0) vs self-managed.
4. **Log persistence**: Postgres-only vs object storage for large logs.

## 10) Risks + Mitigations

1. **Unsafe script execution**
   - Mitigation: strict allowlist, sanitized args, isolated worker user.

2. **Long-running jobs blocking queue**
   - Mitigation: separate queues by priority/runtime class.

3. **SEO regression from monetization clutter**
   - Mitigation: phased rollout, template-level caps, ranking guardrails.

4. **Operational fragility**
   - Mitigation: retries, dead-letter queue, alerting, runbooks.

## 11) Definition of Done (MVP)

- Admin can trigger at least 3 core scripts from UI.
- Every run has structured status and retrievable logs.
- Failed jobs can be retried from UI.
- Schedule at least one daily script.
- Audit records exist for run/cancel/retry/schedule edits.
- Monetization pilot runs on a controlled subset with KPI dashboard.

## 12) Immediate Next Actions

1. Create `script_registry.json` with 5 initial allowlisted scripts and param schemas.
2. Scaffold API server with `/scripts`, `/jobs`, `/jobs/{id}/logs`.
3. Implement worker process that executes registry commands safely.
4. Stand up minimal admin page (login + run script + jobs list).
5. Add one monetization module to a single template behind feature flag.
