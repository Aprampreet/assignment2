# CODEX MASTER IMPLEMENTATION PROMPT — MEDORA HEALTHCARE

## 1. Mission and execution rules

Build a polished, runnable healthcare management platform for a Django backend hiring assignment. Deliver working code, not merely a plan, mockup, or scaffolding. The product must demonstrate secure multi-role authorization, scalable relational modeling, efficient queries, and a restrained, professionally designed healthcare website.

Inspect the repository first. Preserve useful existing code and conventions; do not overwrite unrelated work. If empty, initialize a monorepo with `backend/` and `frontend/`. Work in milestones, run migrations and tests after each backend milestone, and run frontend lint, typecheck and production build. Do not claim tests passed unless executed. Document blockers and actual results. Never commit secrets. Use synthetic data only. Do not add appointments, payments, prescriptions, hospital ERP modules, RAG, Celery or microservices. Keep exactly 25 business API operations (documentation and infrastructure health probes excluded).

## 2. Stack and architecture

- Django, Django REST Framework, Django Ninja, Supabase managed PostgreSQL, SimpleJWT; supported compatible versions pinned in dependency files.
- Next.js App Router, TypeScript strict mode, Tailwind CSS, shadcn/ui primitives, TanStack Query, React Hook Form, Zod, Lucide icons.
- DRF owns the original 16 operations and six account-management extensions; Ninja owns three read/assistant operations. Both use the same Django ORM, authenticated database user, services, selectors and authorization policies. Do not duplicate CRUD in Ninja.
- Docker Compose for backend and frontend; Supabase is the default development and deployment database. An optional isolated local PostgreSQL service is for tests only; optional Redis for distributed throttling. No mandatory paid infrastructure. Provide environment examples and a local development path without Docker for the application processes.
- Organize Django into accounts, patients, doctors, mappings, audit, dashboard and assistant apps. Use thin views/routers, explicit serializers/schemas, domain services for writes, selectors for complex reads, and shared policies. Avoid unnecessary repository abstractions over the ORM.

### Supabase database integration — mandatory

- Use Supabase exclusively as the managed PostgreSQL provider for the application. Django ORM and Django migrations own the schema. Do not use Supabase Auth, PostgREST, client-side database queries, or a Supabase JavaScript SDK for database access. SimpleJWT and Django authorization remain authoritative.
- Install and pin compatible psycopg and dj-database-url dependencies. Read DATABASE_URL from backend-only environment variables; never expose it through NEXT_PUBLIC variables, browser bundles, logs or Git. Supply placeholders in .env.example, never real credentials. Use the connection string copied from the Supabase Connect panel; prefer the direct connection when IPv6 connectivity is available, otherwise the session pooler (typically port 5432) for persistent Django processes and migrations. Do not default to transaction pooling. Require TLS (sslmode=require at minimum; verify-full with trusted CA where configured). Use bounded connection lifetime and connection health checks, and budget connections across workers.
- Configure a dedicated non-public application schema and a controlled search_path for Django, including migrations and auth tables. Document one-time schema/role provisioning SQL, required privileges and how to run migrations. Keep application tables out of schemas exposed through Supabase Data API; disable Data API if unused, or explicitly restrict exposed schemas and revoke unnecessary anon/authenticated grants. Do not rely on Supabase RLS to enforce Django user permissions. Use separate migration and runtime database credentials where practical, with least-privilege runtime grants. Never use a service-role API key as a database password.
- If transaction pooling is explicitly required later, configure compatible driver behavior (disable server-side cursors and automatic prepared statements as appropriate), and use a direct/session connection for migrations. Test before enabling it.
- Provide DATABASE_URL and optional MIGRATION_DATABASE_URL examples, plus an isolated TEST_DATABASE_URL for automated tests. Refuse to run destructive test setup, flush or demo seeding against production/shared databases. CI uses a disposable PostgreSQL service with the same schema constraints. Never silently fall back to SQLite.
- README must explain Supabase project creation, Connect panel, password URL encoding, environment setup, schema provisioning, migrate, bootstrap_admin, dev-only seed_demo, connectivity troubleshooting and connection limits. Do not require paid Supabase features. Do not claim a live database connection or successful migration until actually verified with supplied credentials.

## 3. Scalable data model — implement before APIs

Use UUID primary keys, timezone-aware timestamps, explicit related names, database constraints and deliberate deletion policies. Create an abstract TimestampedModel with created_at and updated_at; use it where meaningful. Do not use JSON for relational data or lists of foreign keys. Do not create indexes blindly: document the query each composite index serves. PostgreSQL is the authoritative test database.

### User (accounts)

Custom user derived from AbstractUser with username removed, or AbstractBaseUser with PermissionsMixin and a fully implemented manager. Set AUTH_USER_MODEL before initial migration. Fields: UUID id, name (150), email (254), role (SUPER_ADMIN, SUPERVISOR, DOCTOR, PATIENT), is_active, is_staff, date_joined, updated_at, created_by nullable self FK with SET_NULL, must_change_password boolean for provisioned accounts. Password is Django's hashed field, never a separate plaintext field. Normalize emails consistently and enforce case-insensitive uniqueness at database level (Lower(email) unique constraint). USERNAME_FIELD=email. Use Django password validators and set_password. Index role/is_active for admin filtering. Enforce one super-admin account using a conditional unique constraint on role where role=super_admin; bootstrap via an idempotent management command using environment-supplied credentials or secure interactive input. No public creation, deletion, deactivation or role change of the singleton administrator. Document emergency recovery. Django is_staff/is_superuser are server-controlled and never writable from public payloads; only the super admin may access Django admin. Business permissions use the role and current DB state, not a client-supplied role or stale JWT claim.

### PatientProfile (patients)

UUID id; user OneToOne AUTH_USER_MODEL with PROTECT; managed_by nullable FK to User with PROTECT (current responsible supervisor, distinct from immutable created_by); created_by nullable FK with SET_NULL; date_of_birth nullable DateField; gender optional choices including unspecified; blood_group optional choices; phone optional validated string; address optional bounded text; allergies and medical_history optional bounded text; archived_at nullable datetime; created_at, updated_at. Name and email come from User, not duplicated. Self-registered patients have no supervisor initially; super admin can allocate them using the existing patient PUT operation. Supervisors can only create patients assigned to themselves, cannot transfer ownership or set arbitrary created_by. Validate DOB not in future, normalize phone, and validate profile/user role consistency in services. Index (managed_by, archived_at, created_at) for supervisor listings; use stable ordering with id tie-breaker. No government IDs or unnecessary sensitive fields.

### Specialization (doctors)

UUID id, name, slug unique, is_active. Case-insensitive unique name. Seed a small curated set through a data migration or seed command. Use a protected FK from DoctorProfile; no extra CRUD endpoints. Supply available specializations as authorized dashboard metadata for management forms. This normalized lookup avoids inconsistent specialty strings and enables indexed filtering.

### DoctorProfile (doctors)

UUID id; user OneToOne AUTH_USER_MODEL with PROTECT; specialization FK PROTECT; managed_by nullable FK PROTECT; created_by nullable FK SET_NULL; registration_number unique after normalization (use fictional values in seed); qualifications bounded text; years_of_experience nonnegative small integer with reasonable maximum; biography bounded text; professional_phone optional; archived_at nullable datetime; created_at, updated_at. Optional avatar only if safely implemented; otherwise use initials and licensed local imagery for public marketing. Do not expose private contact fields in directory responses. Index (specialization, archived_at) and (managed_by, archived_at, created_at). Doctor can edit only biography, qualifications and permitted professional contact fields; registration number, specialization, ownership and identity fields remain management-controlled.

### PatientDoctorMapping (mappings)

UUID id; patient FK PROTECT; doctor FK PROTECT; assigned_by FK SET_NULL; assigned_at; ended_at nullable; ended_by nullable FK SET_NULL; optional assignment_reason bounded text (not clinical notes). A mapping is active when ended_at is null. Conditional UniqueConstraint(patient, doctor) where ended_at is null prevents duplicate active assignments while allowing reassignment history. Check ended_at >= assigned_at when present. Composite indexes (patient, ended_at), (doctor, ended_at) support both directions. No redundant ManyToMany field unless explicitly using this through model. DELETE ends the active mapping rather than destroying history. Create/end operations are atomic; catch uniqueness conflicts outside the atomic block and return 409. Lock affected profile rows in consistent order when assigning, archiving or transferring to prevent races; recheck active state and authorization inside the transaction. Do not allow assignments to archived profiles or inactive users.

### AuditLog (audit)

UUID id, actor nullable FK SET_NULL, action enum, resource_type enum, resource_id UUID nullable, request_id UUID, created_at, outcome enum, metadata JSONField limited to allowlisted non-sensitive operational metadata (e.g. changed field names, never values). Append-only through application services; no edit/delete UI or API. Index (actor, created_at), (resource_type, resource_id, created_at), and created_at for recent activity. Never store passwords, JWTs, raw request bodies, medical history or AI messages. Successful sensitive mutations and their audit events commit together. Security failure logging must survive rolled-back transactions where appropriate. Do not claim database-level immutability unless enforced. Document retention and production access restrictions.

### Lifecycle and invariants

- Create user and corresponding profile atomically. Every doctor/patient account has exactly one matching profile; supervisors/admin have neither. Cross-table role invariants enforced in shared services and tested; do not pretend a normal CheckConstraint can span tables.
- Archive patient/doctor through DELETE: set archived_at, deactivate user and end active mappings in one transaction; retain historical data. Repeated delete may return 404; document semantics. Do not allow account reactivation through generic user PATCH if profile remains archived. Account suspension alone is distinct from archival; suspend access immediately and exclude inactive profiles from active assignment queries.
- Ownership transfer is super-admin only and does not silently alter existing mappings; new supervisor sees the transferred record and its authorized mappings. created_by is immutable provenance. A supervisor can assign any active doctor from the directory to a patient they manage, but cannot edit another supervisor's doctor. This is intentional.
- Use explicit update field allowlists; no writable nested user/role objects. Do not expose sensitive model fields via `fields = '__all__'`.
- Provide migrations, ER diagram in README (Mermaid), model constraints tests and representative query-count tests. No automatic production seed data.

## 4. Roles and access policy

Four roles only. Super admin manages all records, creates supervisors, transfers ownership, suspends accounts, views audit logs. Supervisor creates doctor/patient accounts, lists and modifies only managed patients/doctors, browses the safe doctor directory, assigns doctors to managed patients, and ends mappings for managed patients. Doctor reads only actively assigned patients and own full doctor profile, browses safe doctor directory, edits allowed own profile fields. Patient reads and edits only own allowed demographic fields, sees own assigned doctors, browses safe directory. Patient cannot edit clinical history/allergies through generic self-service if designated management-only; document field policy. No role except management can create or end mappings. No supervisor may manage supervisors or elevate privileges.

Apply role checks AND object-level scoping on every read/write, including nested lookups, filters, counts, audit and AI tools. Scope querysets before lookup; return 404 for inaccessible objects, 403 for disallowed operations. Use role-specific response serializers: doctor directory excludes ownership, private email and sensitive account data; doctors see only relevant patient data; patient sees own profile. All authenticated roles may list doctors with safe fields, preserving the assignment's directory requirement. Admin sees all; supervisor patient listing is ownership-scoped; doctor patient listing is active-assignment-scoped; patient listing returns only self. Mapping list and patient-specific lookup follow the same policy; doctors see only their own mappings, not other doctors' assignments to the same patient.

Public registration always creates PATIENT regardless of input; reject privilege fields. A seeded supervisor account enables reviewers to exercise all mandatory CRUD operations. Explain in README that role restrictions intentionally strengthen the assignment's generic authenticated-user permissions.

## 5. API contract — exactly 25 business operations

Preserve original assignment routes and HTTP methods exactly. UUID path converters. DRF routes have trailing slash; Ninja extensions use the documented trailing slash. For mappings, GET and DELETE share the same dynamic path but interpret the UUID as patient ID and mapping ID respectively; implement one explicit dispatch view or equivalent method-specific handling and document it clearly. Do not register competing ambiguous URL patterns.

| # | Method | Path | Purpose |
|---|---|---|---|
| 1 | POST | /api/auth/register/ | Public patient registration: name, email, password |
| 2 | POST | /api/auth/login/ | Email/password, access and refresh JWT |
| 3 | POST | /api/patients/ | Management creates patient account/profile |
| 4 | GET | /api/patients/ | Scoped patient list |
| 5 | GET | /api/patients/{id}/ | Scoped detail |
| 6 | PUT | /api/patients/{id}/ | Role-specific update |
| 7 | DELETE | /api/patients/{id}/ | Archive patient |
| 8 | POST | /api/doctors/ | Management creates doctor account/profile |
| 9 | GET | /api/doctors/ | Safe doctor directory |
| 10 | GET | /api/doctors/{id}/ | Role-specific detail |
| 11 | PUT | /api/doctors/{id}/ | Role-specific update |
| 12 | DELETE | /api/doctors/{id}/ | Archive doctor |
| 13 | POST | /api/mappings/ | Assign doctor to patient |
| 14 | GET | /api/mappings/ | Scoped mappings |
| 15 | GET | /api/mappings/{patient_id}/ | Assigned doctors, scoped |
| 16 | DELETE | /api/mappings/{id}/ | End assignment |
| 17 | POST | /api/auth/refresh/ | Rotate JWT refresh token |
| 18 | POST | /api/auth/logout/ | Blacklist caller's refresh token |
| 19 | GET | /api/auth/me/ | Current identity, role, profile ID, password-change flag |
| 20 | GET | /api/users/ | Admin-only user list |
| 21 | POST | /api/users/ | Admin-only supervisor creation |
| 22 | PATCH | /api/users/{id}/ | Admin account status/allowed metadata; self password change only with current password |
| 23 | GET | /api/v1/dashboard/ | Ninja role-scoped statistics and form metadata |
| 24 | GET | /api/v1/audit-logs/ | Ninja admin-only paginated audit events |
| 25 | POST | /api/v1/assistant/chat/ | Ninja authenticated lightweight AI assistant |

For #22, implement separate explicit payload schemas/branches for admin management and self password change; never accept role changes. Provisioned accounts receive a temporary password through an authorized operator (not logged or stored plaintext), must change it before accessing business APIs, and may use login, me, refresh, logout and their own password-change branch only. On password change revoke outstanding refresh tokens and reject old access tokens using SimpleJWT password-revocation support or an equivalent tested token-version mechanism. No public password reset flow in this scope; document limitation. Do not silently enable default ViewSet PATCH routes for patients/doctors.

Use 201 create, 200 read/update, 204 delete, 400 validation, 401 authentication, 403 role denial, 404 inaccessible/not found, 409 conflict, 429 throttle. Stable error shape with code, message, field_errors and request_id; preserve useful DRF validation details. Paginate lists (default 20, max 100), allowlist filters and sort fields, use deterministic ordering. Support search by permitted names, specialization filter, active status (admin only where applicable), mapping patient/doctor IDs, and date filters for audit. Never allow filters to broaden scope. PUT uses a documented complete role-specific writable representation. Generate OpenAPI for both frameworks and an importable Postman collection with variables and example bodies for all 25 operations.

## 6. Security and performance acceptance criteria

- SimpleJWT short-lived access (~5 minutes), refresh (~24 hours), rotation and blacklist enabled. Authenticate against current active user on every DRF and Ninja request; never use stateless token user for authorization. Logout revokes refresh; document remaining access lifetime unless token-version revocation implemented. Validate refresh ownership and active status. Handle refresh races in browser with single-flight coordination and safe retry behavior.
- Next.js BFF stores tokens in HttpOnly, Secure in production, SameSite cookies; no localStorage tokens, no tokens exposed to browser JS. BFF forwards Bearer tokens to Django. Direct API clients can still use standard JWT responses. BFF must allowlist upstream routes/methods, reject arbitrary proxy targets, validate CSRF token and Origin on unsafe requests, and prevent caching authenticated responses. Do not forward arbitrary client headers or cookies upstream. Clear cookies on logout/failure. Frontend route guards are UX only.
- Argon2 password hashing with supported fallback; strong password validation; generic login errors; rate limit login by IP and normalized identity, registration and AI by appropriate keys. Redis-backed shared cache if configured; document local cache limitations and use atomic limiter or edge controls for production. Trust forwarded IP only from configured proxies.
- Explicit ALLOWED_HOSTS, CORS allowlist if needed, HTTPS, production secure cookies/HSTS, DEBUG false, environment secrets, CSP, clickjacking protection. Configure trusted proxy settings only for actual deployment. No wildcard credentials CORS. Never log auth headers or medical payloads. Use no-store for sensitive responses. Do not expose stack traces.
- Use select_related for user/specialization and prefetch_related for scoped relationships; annotate dashboard counts and use aggregate queries instead of Python loops. Avoid N+1, unbounded queries, and shared caches of private records. If caching aggregates, key by user/scope and invalidate on writes; prefer no cache initially. Use PostgreSQL EXPLAIN where helpful, document measured results only.
- Audit account creation/status changes, password changes (no secrets), patient/doctor mutations, ownership transfers and mapping changes. Record correlation IDs. Add liveness/readiness probes as infrastructure routes if necessary; do not count them as business APIs.
- No claims of HIPAA/DPDP compliance or production certification. This is a synthetic-data demonstration; document real-world privacy, consent, retention, encryption and operational review requirements.

## 7. Frontend — art direction and actual behavior

Brand: Medora Healthcare. Build a premium private-clinic website and a practical healthcare operations workspace. The design must look intentionally human-designed, not like a generic AI SaaS template. Use warm white #F8F9F7, white #FFFFFF, deep navy #122B39, medical teal #176B60, sage #E8F0EC, muted slate text. DM Sans or Manrope for interface, restrained editorial serif for marketing hero only. Strong hierarchy, generous public-page whitespace, compact dashboard density, subtle 1px borders, 6–10px radii, restrained shadows. No gradients, glassmorphism, glowing buttons, decorative blobs, excessive pills, random eyebrow labels, fake statistics, fake testimonials, emoji icons or AI sparkle branding. Use locally stored licensed healthcare photography or clearly labeled placeholders; never fabricate real doctor identities. No external image hotlink dependencies.

Public homepage: polished wordmark, simple nav, login and register CTA, large horizontal editorial hero with realistic doctor photography, concise service/platform introduction, healthcare workflow explanation, and professional footer. Public pages are informational; do not expose protected doctor records to unauthenticated visitors or add extra public API operations. Directory is available after login. Include accessible login/register forms, password visibility, meaningful validation, and clear redirects. Public site should not pretend to be an actual licensed clinic.

Dashboard: shared shell with desktop sidebar, compact top bar, breadcrumbs, responsive mobile navigation, profile menu and logout. Role-based navigation and landing pages. Super admin overview: real counts, supervisor table, doctors, patients, assignments, recent audit activity, account status controls. Supervisor: managed patient/doctor counts, searchable tables, add/edit forms, assignment dialog, recent scoped activity. Doctor: assigned patient list, patient detail with authorized fields, own profile editor, directory. Patient: personal profile, assigned doctor cards, directory, permitted self-edit. Use actual API data; no hardcoded dashboard metrics. Charts only if real aggregate data supports them; otherwise use clean count cards and lists.

Tables: server pagination, debounced search, filters, sorting, useful columns, clear empty states, row actions, confirmation dialogs for archive/end assignment. Forms: accessible labels, inline field errors, pending states, duplicate submission prevention, toast feedback, preserve input on errors. Assignment dialog searches active doctors and prevents duplicate selection. Use TanStack Query scoped keys; clear query cache on logout or account change. Avoid exposing private records in URLs beyond opaque IDs. All buttons must work or be omitted. No fake interactions. Test desktop, tablet and mobile; keyboard navigation, focus management, contrast and reduced-motion support.

## 8. Small AI assistant

One floating bottom-right chat launcher on authenticated dashboards; compact panel, clear close button, accessible focus, role-relevant suggested questions, message loading/error/retry, mobile full-width behavior. No separate AI page. Keep conversation history in frontend memory only; clear on logout. Use Gemini or Groq via server-side provider adapter with environment key, model configuration, bounded timeout, token budget and rate limits. No API key in frontend. No vector DB or agent framework.

Assistant supports platform help and safe role-specific aggregate questions (e.g. number of assigned patients, managed patients, active supervisors, how to find assigned doctors). Use deterministic allowlisted intents/tools backed by shared selectors; authorize every call against the current user. Never pass raw patient records, names, emails, clinical history, tokens or arbitrary SQL to the provider. Prefer local deterministic responses for data lookups; send only non-identifying aggregates or sanitized generic FAQ input to LLM. Do not forward arbitrary free text containing health/identity data; constrain provider inputs to approved intents and sanitized templates. No diagnosis, prescriptions, medical advice, destructive actions or arbitrary tool execution. Treat user input and model output as untrusted; render plain text or sanitized Markdown, never raw HTML. Reject prompt injection attempts to access other users' data. If no key/provider unavailable, return an honest deterministic help response or clear unavailable status; do not fake LLM output. Test provider with mocks.

## 9. Testing and deliverables

Use pytest-django with an isolated local or CI PostgreSQL database (never the shared Supabase application database), factories and parameterized role tests. Cover all 16 required operations with happy paths and validation; all nine extensions; unauthenticated requests; cross-supervisor isolation; cross-patient isolation; doctor assignment isolation including ended mappings; role escalation payloads; private directory fields; duplicate case-insensitive emails; singleton admin; duplicate concurrent mapping creation; atomic rollback of user/profile and audit; archive/assignment race; ownership transfer; inactive users and token refresh; temporary password restrictions; password-change revocation; rate limiting; AI tool scope and provider failure; pagination and query counts. Use TransactionTestCase or transactional pytest tests with independent DB connections for concurrency. Add frontend tests for critical role flows and BFF CSRF/auth behavior; use Playwright smoke tests if available. Run actual commands and report results.

Deliver README with setup commands, architecture, ER diagram, role matrix, exact 25-operation API inventory, assignment coverage, security decisions, known limitations, demo instructions and deployment guidance. Include .env.example, Dockerfiles, compose.yaml, migrations, seed_demo command (idempotent, explicit dev-only guard), bootstrap_admin command, Postman collection and environment template, DRF drf-spectacular docs and Ninja OpenAPI docs, GitHub Actions for backend tests and frontend lint/typecheck/build. Protect or disable interactive docs in production as appropriate. Demo accounts for all four roles with synthetic data, credentials supplied via local environment; never publish a privileged production demo password. Provide deployment instructions for Vercel and a Django host with Supabase managed PostgreSQL; do not claim deployment unless actually done.

## 10. Implementation sequence and definition of done

1. Inspect repo, establish scope and dependency versions, scaffold config and Supabase PostgreSQL connectivity.
2. Implement custom user, normalized models, constraints, migrations, bootstrap/seed, shared policies and services.
3. Implement and test original 16 DRF operations before extensions.
4. Add six DRF extensions and three Ninja endpoints; test authorization, security, concurrency and performance.
5. Build public site, auth BFF and shared role dashboard; wire all forms and tables to real APIs.
6. Add lightweight AI panel and provider adapter; test safe fallback.
7. Run migrations, seed local demo, execute tests, lint, typecheck and build; inspect responsive screens if browser tooling exists. Fix failures, not merely document avoidable errors.
8. Finish README, API docs, Postman, CI and deployment instructions. Report implemented features, exact test results, remaining limitations and run commands.

Acceptance: a reviewer can start the app, log in as each role, exercise all original endpoints, create a supervisor, create patient and doctor accounts, assign/unassign doctors, verify cross-role access denial, view real dashboard data and use the small assistant. No placeholder business logic, no fabricated metrics, no extra business endpoints, no unnecessary infrastructure. Prioritize correctness and security over decorative complexity.
