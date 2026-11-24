"""Generate the importable reviewer collection from the documented operation inventory."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs"
IDENTITY = {"name": "Sample Person", "email": "{{new_email}}", "password": "{{temporary_password}}"}
PATIENT = {"name": "Sample Patient", "date_of_birth": None, "gender": "unspecified", "blood_group": "", "phone": "", "address": "", "allergies": "", "medical_history": ""}
DOCTOR = {"name": "Sample Doctor", "specialization": "{{specialization_id}}", "registration_number": "DEMO-001",
          "qualifications": "Fictional credentials", "biography": "", "professional_phone": "", "years_of_experience": 8}
OPS = [
    ("Register", "POST", "auth/register", {**IDENTITY, "role": "patient"}),
    ("Login", "POST", "auth/login", {"email": "{{email}}", "password": "{{password}}", "portal": "patient"}),
    ("Create patient", "POST", "patients", {**IDENTITY, "email": "sample-patient@example.com"}),
    ("List patients", "GET", "patients", None),
    ("Patient details", "GET", "patients/{{patient_id}}", None),
    ("Update patient", "PUT", "patients/{{patient_id}}", PATIENT),
    ("Archive patient", "DELETE", "patients/{{patient_id}}", None),
    ("Create doctor", "POST", "doctors", {**IDENTITY, **DOCTOR, "email": "sample-doctor@example.com"}),
    ("List doctors", "GET", "doctors", None),
    ("Doctor details", "GET", "doctors/{{doctor_id}}", None),
    ("Update doctor", "PUT", "doctors/{{doctor_id}}", DOCTOR),
    ("Archive doctor", "DELETE", "doctors/{{doctor_id}}", None),
    ("Assign doctor", "POST", "mappings", {"patient_id": "{{patient_id}}", "doctor_id": "{{doctor_id}}"}),
    ("List mappings", "GET", "mappings", None),
    ("List patient mappings", "GET", "mappings/{{patient_id}}", None),
    ("End assignment", "DELETE", "mappings/{{mapping_id}}", None),
    ("Refresh session", "POST", "auth/refresh", {"refresh": "{{refresh_token}}"}),
    ("Logout", "POST", "auth/logout", {"refresh": "{{refresh_token}}"}),
    ("Current identity", "GET", "auth/me", None),
    ("List accounts", "GET", "users", None),
    ("Create admin or supervisor", "POST", "users", {**IDENTITY, "email": "sample-supervisor@example.com", "role": "supervisor"}),
    ("Update account or change own password", "PATCH", "users/{{user_id}}", {"is_active": False}),
    ("Workspace dashboard", "GET", "v1/dashboard", None),
    ("List audit events", "GET", "v1/audit-logs", None),
    ("Ask assistant", "POST", "v1/assistant/chat", {"message": "How do I use the directory?"}),
]
COLLECTION = {
    "info": {
        "name": "Medora Healthcare",
        "description": "All 25 operations. Run individually with the appropriate role and environment.",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}]},
    "item": [],
}
for index, (name, method, route, payload) in enumerate(OPS, 1):
    request = {"method": method, "url": "{{base_url}}/api/" + route + "/", "header": [{"key": "Accept", "value": "application/json"}]}
    if payload is not None:
        request["header"].append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {"mode": "raw", "raw": json.dumps(payload, indent=2), "options": {"raw": {"language": "json"}}}
    if route in {"auth/login", "auth/refresh", "auth/register"}:
        request["auth"] = {"type": "noauth"}
    if index in {6, 11}:
        request["description"] = "Example is a supervisor PUT. For the super admin add managed_by (UUID or null). See the API contract for self edits."
    if index == 1:
        request["description"] = "Set role to doctor or supervisor for admin approval. Doctor requests also need specialization_slug and registration_number."
    if index == 2:
        request["description"] = "Set portal to doctor or supervisor as appropriate. Administrators use supervisor."
    if index == 22:
        request["description"] = 'For approval use {"is_active":true,"approval_pending":false}. For your own password use {"current_password":"{{password}}","password":"{{new_password}}"}.'
    item = {"name": f"{index}. {name}", "request": request}
    if route in {"auth/login", "auth/refresh"}:
        item["event"] = [{
            "listen": "test",
            "script": {"type": "text/javascript", "exec": [
                "if (pm.response.code === 200) {",
                "  const tokens = pm.response.json();",
                "  pm.environment.set('access_token', tokens.access);",
                "  pm.environment.set('refresh_token', tokens.refresh);",
                "}",
            ]},
        }]
    COLLECTION["item"].append(item)

ENVIRONMENT = {
    "name": "Medora local placeholder environment",
    "_postman_variable_scope": "environment",
    "values": [{"key": "base_url", "value": "http://127.0.0.1:8000", "enabled": True}] + [
        {"key": key, "value": "", "type": "secret" if key in {"password", "new_password", "temporary_password", "access_token", "refresh_token"} else "default", "enabled": True}
        for key in ("email", "password", "new_email", "new_password", "temporary_password", "access_token", "refresh_token",
                    "specialization_id", "patient_id", "doctor_id", "mapping_id", "user_id")
    ],
}

for filename, data in [("medora.postman_collection.json", COLLECTION), ("medora.postman_environment.json", ENVIRONMENT)]:
    (ROOT / filename).write_text(json.dumps(data, indent=2) + "\n")
