# Medora Healthcare

Medora is a healthcare coordination platform for four roles. Patients see their care team, doctors see their assigned patients, supervisors manage records and assignments, and super admins manage accounts and approvals. The project uses synthetic data and is designed as a technical demonstration.

**Live application:** [Open Medora Healthcare](https://assignment2-gold-one.vercel.app/)

[Product and engineering specification](dicription.md) · [API contract](docs/api.md) · [Postman collection](docs/medora.postman_collection.json) · [DRF OpenAPI](docs/drf.openapi.yaml) · [Ninja OpenAPI](docs/ninja.openapi.json)

## What you can do

- Register as a patient and enter the workspace immediately.
- Request a doctor or supervisor account, then wait for a super admin to approve it.
- Sign in through Patient, Doctor, or Supervisor / Admin access.
- Create and manage patients, doctors, supervisors, and additional super admins according to role.
- Assign doctors to patients and retain assignment history when an assignment ends.
- Browse a safe doctor directory and ask the workspace assistant about navigation or authorized counts.

## Architecture

```mermaid
flowchart LR
    Browser[Next.js browser UI] --> BFF[Next.js API route]
    BFF --> DRF[Django REST Framework]
    BFF --> Ninja[Django Ninja]
    DRF --> Policy[Shared policies and services]
    Ninja --> Policy
    Policy --> ORM[Django ORM]
    ORM --> DB[(Supabase PostgreSQL\nprivate medora schema)]
    Ninja --> Assistant[Allowlisted assistant intents]
    Assistant -. approved generic help only .-> Groq[Optional Groq API]
```

Django handles all database access. The frontend keeps JWTs in HttpOnly cookies through its same-origin BFF. The Supabase publishable key is not needed. The assistant answers scoped counts locally and sends only fixed navigation instructions to Groq when a provider key is configured.

## Start locally without Docker

Use Python 3.13, Node.js 22, and the configured Supabase project. Copy `.env.example` to `.env` and fill in the private values. Keep `.env` outside version control. The current workspace already has a local `.env` with the Supabase connection and a generated bootstrap administrator password.

From the repository root:

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python backend/manage.py migrate
.venv/bin/python backend/manage.py bootstrap_admin
.venv/bin/python backend/manage.py runserver 127.0.0.1:8000
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Create `frontend/.env.local` with:

```dotenv
DJANGO_API_ORIGIN=http://127.0.0.1:8000
```

Open `http://localhost:3000`. Select **Supervisor / Admin** to sign in as an administrator. The BFF checks the browser Origin against the URL receiving the request and verifies its CSRF cookie and header. The bootstrap command is idempotent for the configured email. To create a second administrator, use **Accounts** → **Add account** → **Super Admin**, or bootstrap with a different email. To change an existing admin password, run `python backend/manage.py changepassword ADMIN_EMAIL` in the configured Python environment.

### Set up a new Supabase project

1. Create a Supabase project and copy its PostgreSQL connection string from **Connect**. Use a direct connection when IPv6 works, or the session pooler on port 5432. Percent-encode special characters in the password.
2. Provision a private schema using [the SQL template](docs/provision-supabase.sql). Configure `DATABASE_SCHEMA=medora` and the backend-only `DATABASE_URL`. Supply `MIGRATION_DATABASE_URL` if migrations use a separate owner role.
3. Keep `medora` out of Supabase Data API exposed schemas and revoke `anon` and `authenticated` access. Django migrations own all tables, including authentication tables.
4. Set `DJANGO_SECRET_KEY` to a strong random value. Run migrations and bootstrap an admin using the commands above.

Django requires TLS for Supabase. Set `DATABASE_SSL_ROOT_CERT` to use hostname verification with a trusted CA. The configured local Supabase connection and migrations were verified. Keep the connection budget within the project's database limit.

## First-use walkthrough

```mermaid
flowchart TD
    Visit[Open Medora] --> Register{Choose account type}
    Register -->|Patient| Active[Account active immediately]
    Register -->|Doctor or supervisor| Pending[Inactive approval request]
    Pending --> Admin[Super admin reviews Accounts]
    Admin --> Approve[Approve request]
    Approve --> Login[Sign in]
    Active --> Login
    Login --> Workspace[Role-specific workspace]
```

For a management walkthrough, sign in as a super admin and create a supervisor under **Supervisors**. The supervisor can create a patient and doctor, then open **Assignments** to connect them. A doctor sees only currently assigned patients. A patient sees only their own profile and active care team. The admin can review changes under **Audit log**.

### Django administration

Super admins can also sign in at `/admin/` with their email and password. This is an operational console with searchable, filtered account, patient, doctor, assignment and audit views. In **Users**, filter by **Approval pending**, select doctor or supervisor requests, then choose **Approve selected doctor and supervisor registrations**. The action uses the account service and writes an audit event for each approval. The **Specializations** section maintains the doctor registration taxonomy.

Profiles, assignments and audit events are read-only in Django admin so changes continue through the role-scoped application services. Create supervisors and additional super admins in the Medora workspace. Run `collectstatic` when deploying Django so the custom admin stylesheet is available.

A developer-only `seed_demo` command can populate synthetic supervisor, doctor, and patient accounts. It requires `DJANGO_DEBUG=1`, `DATABASE_SCHEMA=medora_demo`, `ALLOW_DEMO_SEED=1`, and `DEMO_PASSWORD` in a dedicated development schema. Run `bootstrap_admin` first. Demo users must change their temporary password on first login. Do not run demo seeding against the shared application schema.

## API and permission model

The project has exactly 25 business operations, with 22 DRF operations and three Ninja operations. See [the full route inventory, request fields, filters, responses, and error codes](docs/api.md). Interactive docs are available in debug at `/api/docs/` and `/api/v1/docs/`.

```mermaid
flowchart LR
    Request[Authenticated request] --> Current[Load current active user]
    Current --> Role[Check current database role]
    Role --> Scope[Scope queryset to owned or assigned objects]
    Scope --> Lookup[Look up UUID]
    Lookup --> Service[Validate and write in transaction]
    Service --> Audit[Write audit event in same transaction]
```

A supervisor can manage only their own patients and doctors, while they may assign any active doctor to a patient they manage. Doctors see patients through active assignments only. Patients see only their own profile and assigned doctors. The directory exposes safe professional fields to all authenticated roles. Pending or suspended users cannot access business operations. Inaccessible objects return 404, disallowed operations return 403, and conflicts return 409.

## Data model

```mermaid
erDiagram
    USER ||--o| PATIENT_PROFILE : has
    USER ||--o| DOCTOR_PROFILE : has
    USER o|--o{ USER : creates
    USER o|--o{ PATIENT_PROFILE : manages
    USER o|--o{ DOCTOR_PROFILE : manages
    SPECIALIZATION ||--o{ DOCTOR_PROFILE : classifies
    PATIENT_PROFILE ||--o{ PATIENT_DOCTOR_MAPPING : receives
    DOCTOR_PROFILE ||--o{ PATIENT_DOCTOR_MAPPING : serves
    USER o|--o{ AUDIT_LOG : acts
```

UUID primary keys, timezone-aware timestamps, normalized specialties, case-insensitive email uniqueness, and a partial unique constraint for active doctor–patient pairs protect the data model. Archival deactivates the profile user and ends active assignments in one transaction. Assignment history and audit entries remain available to authorized management users. [The detailed model and lifecycle specification](dicription.md#data-model-and-lifecycle) documents ownership, deletion, and index choices.

## Tests and checks

Tests require a **disposable local PostgreSQL** server with a `medora_test` database and a role that can create test databases. The test runner checks the URL and refuses a shared Supabase host. Set `TEST_DATABASE_URL` to that local server, then run:

```bash
cd backend
TEST_DATABASE_URL=postgresql://medora:medora-test-only@127.0.0.1:55432/medora_test ../.venv/bin/pytest -q
cd ../frontend
npm run lint
npm run typecheck
npm run build
```

The repository also includes Chromium smoke tests in `frontend/e2e`. Run `npm run test:e2e` against a disposable seeded environment after setting the `E2E_*` variables in [the test file](frontend/e2e/workspace.spec.ts). CI runs PostgreSQL API tests and the frontend checks in `.github/workflows/ci.yml`.

### Verification evidence

On 24 November 2026, the isolated PostgreSQL suite passed **24 tests**. The browser suite passed **6 Chromium scenarios** covering public layouts, BFF rejection rules, patient registration and self-edit, super admin account management, supervisor assignment changes, and doctor mobile access. Frontend lint, type checking, and production build passed. These are local results; the repository CI and a public Render deployment need separate verification.

The permission tests exercise unauthenticated denial, cross-supervisor record isolation, doctor access through active assignments, patient access to their own records, directory field privacy, pending-account denial, temporary-password restrictions, account approval, and Django admin restrictions. Lifecycle tests exercise duplicate active mapping prevention, concurrent assignment attempts, archive behavior, token revocation, audit rollback, and throttling. See [the API tests](backend/tests/test_api.py) and [the admin tests](backend/tests/test_admin.py) for the executable assertions.

The query-budget test creates 20 managed patients and 20 managed doctors in the disposable database. A supervisor's patient list used **3 database queries** at page sizes 1 and 20; the doctor list also used **3 queries** at both page sizes. The supervisor dashboard used **6 queries** in that fixture. This checks that list serialization does not add one query per row; the numbers are measurements for this fixture and environment, not universal latency guarantees. Reproduce them with `pytest -q -s tests/test_api.py::test_list_query_counts_do_not_grow_with_page_size` from `backend` using `TEST_DATABASE_URL`.

## Deployment and operation

Deploy Django to a Python/Gunicorn host and Next.js to a Node host such as Vercel. Put the two backend-only origins in the Next.js server environment. Run migrations as a one-off task with the migration database role. Serve Django admin static files, use HTTPS, explicit host and proxy settings, and `DJANGO_DEBUG=0`. Set a shared Redis cache or edge rate limits for multi-worker production. The local in-memory limiter applies per process.

For a Render Python web service, set **Root Directory** to `backend`, **Build Command** to `bash build.sh`, and **Start Command** to `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 30`. The build script installs dependencies, collects WhiteNoise static assets, and applies migrations. Render Free does not provide a separate pre-deploy command, so migrations run during the build. Use a Supabase **Session pooler** URL from the project's **Connect** dialog on port 5432 for `DATABASE_URL`, and for `MIGRATION_DATABASE_URL` if configured. Its username is `postgres.<project-ref>` and its hostname is the exact pooler host shown by Supabase; the host cannot be inferred reliably from the project region. The direct Supabase host normally requires IPv6, which Render cannot use. Set `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=<your-backend>.onrender.com`, and `TRUST_HTTPS_PROXY=1` on Render. Set `DJANGO_API_ORIGIN` on Vercel to the Render backend URL. `DJANGO_ALLOWED_HOSTS` accepts hostnames only, without `https://` or a trailing slash. `.python-version` pins the repository to Python 3.13.5.

### Demo keep-alive

`GET /health/` on Django is a public, database-free liveness probe. `GET /api/health` on Vercel forwards the request to that Django route with caching disabled. The [scheduled GitHub Actions workflow](.github/workflows/keep-render-awake.yml) calls the Vercel route at minutes 5, 19, 33, 47, and 59 of each hour, so planned gaps are at most 14 minutes. The default target is `https://assignment2-gold-one.vercel.app/api/health`; set the `MEDORA_PING_URL` GitHub Actions repository variable if that frontend URL changes. Vercel must have `DJANGO_API_ORIGIN` set to the public Render backend URL for the proxy to reach Render. Run the workflow manually once with **Run workflow** and confirm it returns `{"status":"ok"}`.

This is a best-effort demo convenience. [GitHub scheduled jobs can run late or be dropped](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows), so a 14-minute schedule cannot guarantee that a [Render Free service never sleeps](https://render.com/docs/free). The endpoint reports process liveness, not database readiness.

Access tokens last five minutes. Refresh tokens rotate and are blacklisted on logout. Password changes invalidate existing JWTs. The browser BFF validates Origin and CSRF tokens for writes, allowlists backend routes, and disables authenticated response caching. Audit data and database backups require restricted operational access. Define data retention and consent procedures before any real-data use. The platform has no public password reset or email delivery flow in this assignment.
