# Medora API contract

Use JSON and the paths below with their trailing slash. Authenticate with `Authorization: Bearer ACCESS_TOKEN` except for registration, login and refresh. Login optionally accepts `portal` (patient, doctor, supervisor); the supervisor portal also admits the administrator. Provisioned users must change their temporary password before entering workspaces. Interactive docs live at `/api/docs/` and `/api/v1/docs/` in debug.

| # | Method | Path | Purpose |
|---|---|---|---|
| 1 | POST | /api/auth/register/ | Public patient signup or pending doctor/supervisor request |
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
| 21 | POST | /api/users/ | Admin-only supervisor or super admin creation |
| 22 | PATCH | /api/users/{id}/ | Admin account status/allowed metadata; self password change only with current password |
| 23 | GET | /api/v1/dashboard/ | Ninja role-scoped statistics and form metadata |
| 24 | GET | /api/v1/audit-logs/ | Ninja admin-only paginated audit events |
| 25 | POST | /api/v1/assistant/chat/ | Ninja authenticated lightweight AI assistant |

Creation returns 201 except for login and refresh, which return 200 with access and refresh JWTs. Reads and updates return 200. Archive, end assignment and logout return 204. Errors contain `code`, `message`, `field_errors` and `request_id`. Validation is 400, authentication is 401, operations unavailable to the role are 403, inaccessible objects are 404, duplicate or incompatible state is 409, and rate limiting is 429. Send JSON bodies for writes. Undefined fields are rejected.

## List parameters

All lists accept `page` and `page_size` (20 default, 100 maximum). Django lists return `count`, `next`, `previous` and `results`. On audit logs, next and previous are page numbers. On DRF lists, they are URLs.

- Patients and doctors accept `search` (name) and `sort` (recent, oldest, name, -name). Admin may use `active=true|false`. Management may use `assignable=true` for active, unarchived patients. Doctors accept `specialization` (UUID). Supervisors may use `managed=true` for their own doctor management list.
- Mappings accept `search` (patient or doctor name), `patient_id`, `doctor_id`, and `sort` (recent, oldest). Management can filter by `active`. The dynamic path uses a patient UUID for GET and a mapping UUID for DELETE.
- Accounts accept `search` (name or email), `role`, `active`, and `sort` (recent, name, -name).
- Audit accepts `start` and `end` UTC dates, inclusive, and `sort` (recent, oldest).

## Write representations

- Registration accepts `name`, `email`, `password`, and optional `role` (patient, doctor, supervisor). Doctor requests also supply `specialization_slug` and `registration_number`. Doctor and supervisor requests await admin approval through `PATCH /api/users/{id}/` with `{"is_active":true,"approval_pending":false}`. Admin account creation accepts `name`, `email`, `password`, and optional `role` (`supervisor` by default or `super_admin`). Doctor creation additionally requires a specialization UUID and registration number. All profile creation fields beyond the required fields are optional. Only the super admin may submit `managed_by`.
- Patient PUT requires the full writable representation. Patient fields are `name`, `date_of_birth` (ISO date or null), `gender`, `blood_group`, `phone`, `address`. Management also supplies `allergies` and `medical_history`. Super admin additionally supplies `managed_by` (supervisor account UUID or null).
- Doctor PUT requires the full writable representation. Doctors supply `qualifications`, `biography`, and `professional_phone`. Management also supplies `name`, `specialization` (UUID), `registration_number` and `years_of_experience`. Super admin additionally supplies `managed_by`.
- Account PATCH takes `name` and/or `is_active` for an admin updating another account. Pending doctors and supervisors require `is_active=true` together with `approval_pending=false` for approval. Self PATCH takes `current_password` and the new `password` only. Sign in again after changing the password.
- Mapping POST takes `patient_id`, `doctor_id` and optional `assignment_reason`. Ending and archiving retain history.
- Chat POST takes `message`, at most 500 characters. The response has `reply` and `source` (workspace, groq, or help).

Import the collection and placeholder environment together. Fill local variables with reviewer-only values. Login and refresh populate Postman token variables. Use a supervisor session for the creation and PUT examples. Use a super admin session for account and audit operations. For profile operations, obtain the record UUID from the creation response or paginated list. For account PATCH, use the user UUID. Dashboard metadata supplies specialization UUIDs.
