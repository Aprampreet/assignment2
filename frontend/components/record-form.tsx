"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { Item, Option, Role } from "@/lib/types";

export type Resource = "patients" | "doctors" | "users";
export type Field = {
  key: string; label: string; type?: "email" | "password" | "date" | "number" | "textarea" | "select";
  options?: Option[]; required?: boolean; max?: number; min?: number; empty?: string;
};

const identity: Field[] = [
  { key: "name", label: "Full name", required: true, max: 150 },
  { key: "email", label: "Email address", type: "email", required: true, max: 254 },
  { key: "password", label: "Temporary password", type: "password", min: 12, max: 128, required: true },
];
const gender: Option[] = [
  { id: "unspecified", name: "Unspecified" }, { id: "woman", name: "Woman" },
  { id: "man", name: "Man" }, { id: "non_binary", name: "Non-binary" },
];
const bloodGroups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((id) => ({ id, name: id }));
const demographics: Field[] = [
  { key: "date_of_birth", label: "Date of birth", type: "date" },
  { key: "gender", label: "Gender", type: "select", options: gender },
  { key: "blood_group", label: "Blood group", type: "select", options: bloodGroups, empty: "Unspecified" },
  { key: "phone", label: "Phone", max: 30 },
  { key: "address", label: "Address", type: "textarea", max: 500 },
];
const clinical: Field[] = [
  { key: "allergies", label: "Allergies", type: "textarea", max: 1000 },
  { key: "medical_history", label: "Medical history", type: "textarea", max: 4000 },
];
const professional: Field[] = [
  { key: "qualifications", label: "Qualifications", type: "textarea", max: 500 },
  { key: "biography", label: "Biography", type: "textarea", max: 2000 },
  { key: "professional_phone", label: "Professional phone", max: 30 },
];

export function profileFields(resource: Resource, role: Role, create: boolean, specialties: Option[], owners: Option[]): Field[] {
  if (resource === "users") return [...identity, { key: "role", label: "Account role", type: "select", options: [{ id: "supervisor", name: "Supervisor" }, { id: "super_admin", name: "Super Admin" }], required: true }];
  const management = role === "super_admin" || role === "supervisor";
  const fields = create ? [...identity] : resource === "patients" || management ? [identity[0]] : [];
  if (resource === "patients") fields.push(...demographics, ...(management ? clinical : []));
  if (resource === "doctors") {
    if (management) fields.push(
      { key: "specialization", label: "Specialization", type: "select", options: specialties, required: true, empty: "Select a specialization" },
      { key: "registration_number", label: "Registration number", required: true, max: 40 },
      { key: "years_of_experience", label: "Years of experience", type: "number", min: 0, max: 75, required: true },
    );
    fields.push(...professional);
  }
  if (role === "super_admin") fields.push({ key: "managed_by", label: "Responsible supervisor", type: "select", options: owners, empty: "Unassigned" });
  return fields;
}

export function RecordForm({ fields, initial, submit, label }: {
  fields: Field[]; initial?: Item; submit: (data: Record<string, string | number | null>) => Promise<void>; label: string;
}) {
  const defaults = Object.fromEntries(fields.map(({ key }) => [key, String(initial?.[key] ?? (key === "years_of_experience" ? 0 : key === "gender" ? "unspecified" : key === "role" ? "supervisor" : ""))]));
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<Record<string, string>>({ defaultValues: defaults });
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const onSubmit = async (values: Record<string, string>) => {
    const data = Object.fromEntries(fields.map(({ key, type }) => [key,
      type === "number" ? Number(values[key]) : (key === "managed_by" || type === "date") && !values[key] ? null : values[key],
    ]));
    try { await submit(data); }
    catch (error) {
      if (error instanceof ApiError) {
        for (const { key } of fields) {
          if (error.fields[key]) setError(key, { message: [error.fields[key]].flat().join(" ") });
        }
      }
      setError("root", { message: error instanceof Error ? error.message : "Please try again." });
    }
  };
  return <form onSubmit={handleSubmit(onSubmit)} className="record-form">
    <div className="form-grid">{fields.map((field) => {
      const id = `record-${field.key}`;
      const bindings = { ...register(field.key), id, required: field.required, "aria-invalid": !!errors[field.key], "aria-describedby": errors[field.key] ? id + "-error" : undefined };
      return <div key={field.key} className={field.type === "textarea" ? "field wide" : "field"}>
        <label htmlFor={id}>{field.label}</label>
        {field.type === "select" ? <select {...bindings}>
          {field.empty && <option value="">{field.empty}</option>}
          {field.options?.map(({ id, name }) => <option key={id} value={id}>{name}</option>)}
        </select> : field.type === "textarea" ? <textarea {...bindings} rows={3} maxLength={field.max} /> :
          field.type === "password" ? <div className="password-input"><input {...bindings} type={revealed[field.key] ? "text" : "password"} minLength={field.min} maxLength={field.max} autoComplete={field.key === "current_password" ? "current-password" : "new-password"} />
            <button type="button" className="text-button" onClick={() => setRevealed({ ...revealed, [field.key]: !revealed[field.key] })}>{revealed[field.key] ? "Hide" : "Show"}</button></div> :
          <input {...bindings} type={field.type ?? "text"} min={field.type === "number" ? field.min : undefined} max={field.type === "number" ? field.max : undefined} maxLength={field.type === "number" ? undefined : field.max} />}
        {errors[field.key] && <small id={id + "-error"} className="field-error">{errors[field.key]?.message}</small>}
      </div>;
    })}</div>
    {errors.root && <p className="error" role="alert">{errors.root.message}</p>}
    <div className="form-actions"><button className="button" disabled={isSubmitting}>{isSubmitting ? "Saving…" : label}</button></div>
  </form>;
}

export function PasswordForm({ id, done }: { id: string; done: () => void }) {
  return <RecordForm label="Change password" fields={[
    { key: "current_password", label: "Current password", type: "password", required: true, max: 128 },
    { key: "password", label: "New password", type: "password", required: true, min: 12, max: 128 },
  ]} submit={async (data) => { await api(`users/${id}`, "PATCH", data); toast.success("Password changed. Sign in again."); done(); }} />;
}
