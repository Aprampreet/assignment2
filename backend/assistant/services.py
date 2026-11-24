"""Scoped workspace answers. Provider input is fixed instructional text only."""
import re

from accounts.models import Role
from config.policies import require
from dashboard.selectors import statistics
from assistant.provider import explain

ALL_ROLES = set(Role.values)
GUIDES = (
    (re.compile(r"^(?:how (?:do|can) i |where (?:can|do) i )(?:find|see|view) (?:my )?(?:assigned )?(?:doctors|care team)$"), {Role.PATIENT}, "Open My care team to see your currently assigned doctors."),
    (re.compile(r"^(?:how (?:do|can) i |where (?:can|do) i )(?:find|see|view) (?:my )?assigned patients$"), {Role.DOCTOR}, "Open Assigned patients and select a patient to view their profile."),
    (re.compile(r"^(?:how (?:do|can) i )(?:assign|add) (?:a )?doctor(?: to a patient)?$"), {Role.SUPERVISOR, Role.SUPER_ADMIN}, "Open Assignments, select Assign doctor, then choose an active patient and doctor."),
    (re.compile(r"^(?:how (?:do|can) i )(?:use|search|filter|browse) (?:the )?(?:doctor )?directory$"), ALL_ROLES, "Open Doctor directory to browse doctors. Search by name or filter by specialization."),
    (re.compile(r"^(?:how (?:do|can) i )(?:edit|update|change) (?:my )?profile$"), ALL_ROLES, "Open My profile and select Edit profile. Administrators and supervisors can edit records in their management lists."),
    (re.compile(r"^(?:how (?:do|can) i )(?:change|reset|update) (?:my )?password$"), ALL_ROLES, "Open your account menu in the top right and select Change password. You will sign in again afterward."),
    (re.compile(r"^(?:how (?:do|can) i )(?:approve|review) (?:a )?(?:doctor|supervisor|registration|request)s?$"), {Role.SUPER_ADMIN}, "Open Accounts, find a pending doctor or supervisor, and select Approve."),
    (re.compile(r"^(?:how (?:do|can) i )(?:create|add) (?:a )?supervisor$"), {Role.SUPER_ADMIN}, "Open Supervisors and select Add supervisor."),
    (re.compile(r"^(?:how (?:do|can) i )(?:end|remove|unassign) (?:a )?(?:doctor )?assignment$"), {Role.SUPERVISOR, Role.SUPER_ADMIN}, "Open Assignments, find the active assignment, and select End assignment."),
)
COUNTS = (
    (re.compile(r"^(?:how many|number of|count of) (?:active )?(?:assigned )?patients (?:do i have|are assigned to me)$"), {Role.DOCTOR}, "patients", "Active assigned patients"),
    (re.compile(r"^(?:how many|number of|count of) (?:active )?patients (?:do i manage|are managed by me)$"), {Role.SUPERVISOR}, "patients", "Active managed patients"),
    (re.compile(r"^(?:how many|number of|count of) (?:active )?supervisors (?:are there|do we have)$"), {Role.SUPER_ADMIN}, "supervisors", "Active supervisors"),
    (re.compile(r"^(?:how many|number of|count of) (?:active )?assignments (?:are there|do i have)$"), ALL_ROLES, "assignments", "Active assignments"),
)


def reply(user, message):
    require(user)
    intent = " ".join(re.sub(r"[?.!]+$", "", message.strip().lower()).split())
    for pattern, roles, field, label in COUNTS:
        if pattern.fullmatch(intent):
            require(user, roles)
            return {"reply": f"{label}: {statistics(user)[field]}.", "source": "workspace"}
    for pattern, roles, instruction in GUIDES:
        if pattern.fullmatch(intent):
            require(user, roles)
            generated = explain(instruction)
            return {"reply": generated or instruction, "source": "groq" if generated else "help"}
    return {"reply": "I can help with workspace navigation and your permitted counts. Try a suggested question, or ask how to find your profile, change your password, or use the directory. Please leave personal and clinical details out of chat.", "source": "help"}
