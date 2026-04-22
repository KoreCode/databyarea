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

## 7.0 Revenue Model Decision (Selected)

**Chosen model:** **Hybrid = Lead Generation + Affiliate**.

### Why this model
- Matches high-intent, local SEO traffic where users are already comparing providers/costs.
- Diversifies revenue: lead payouts for service requests + affiliate commissions for tools/services that do not require form fills.
- Works with phased rollout: start with lightweight affiliate blocks, then scale geo-routed lead forms once QA and routing are stable.

### Service stack recommendation (phase 1)
1. **Lead generation routing/tracking:** LeadProsper (or equivalent) for buyer routing, caps, and ping/post controls.
2. **Affiliate tracking/network:** Impact (or equivalent) for broad advertiser coverage and reliable partner reporting.
3. **Fallback/expansion options:** Everflow + direct partner deals once volume justifies custom terms.

### Operating rule
- Default monetization template for high-intent pages should include both: one affiliate module and one lead form block, with strict UX caps and disclosure compliance.

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

## 11.1) Definition of "Near Complete" (pre-GA gate)

The project is considered **near complete** only when all checklist items below are true for **2 consecutive weeks**:

### Product + delivery checklist
- Core script-runner workflows are stable in production (p95 job success rate >= 98% and no Sev-1 incidents for 14 days).
- Analytics is live end-to-end (events from admin + monetized page templates visible in dashboards within 15 minutes).
- Payments are live for at least one monetization path (affiliate payout tracking or lead billing reconciliation active and verified weekly).
- Onboarding flow is complete for internal operators (new operator can sign in, run a script, inspect logs, and schedule a job in <= 15 minutes without developer help).
- At least one growth loop is active (example: geo-page CTA -> lead capture -> follow-up email/report -> return visit path is instrumented and running).

### KPI gates (must all be met)
- **Traffic:** >= 50,000 organic sessions/month on monetized templates.
- **Conversion:** >= 2.5% visitor-to-lead conversion on pages with lead modules.
- **MRR:** >= $8,000 monthly recurring revenue (or MRR-equivalent from repeating affiliate/lead contracts).
- **Churn:** <= 4.0% monthly revenue churn across paying partners/customers.

### KPI measurement notes
- Traffic source of truth: GA4/Search Console blended reporting, reviewed weekly.
- Conversion source of truth: server-side lead events matched to unique session IDs.
- MRR source of truth: finance ledger with monthly close and reconciled payouts.
- Churn formula: `(MRR lost in month) / (MRR at start of month)`.

## 12) Immediate Next Actions

1. Create `script_registry.json` with 5 initial allowlisted scripts and param schemas.
2. Scaffold API server with `/scripts`, `/jobs`, `/jobs/{id}/logs`.
3. Implement worker process that executes registry commands safely.
4. Stand up minimal admin page (login + run script + jobs list).
5. Add one monetization module to a single template behind feature flag.
