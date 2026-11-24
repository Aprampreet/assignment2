export type Role = "super_admin" | "supervisor" | "doctor" | "patient";
export interface Identity {
  id: string;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  profile_id: string | null;
  must_change_password: boolean;
}
export interface Item {
  id: string;
  [field: string]: string | number | boolean | null | undefined;
}
export interface Page<T> {
  count: number;
  next: number | boolean | null;
  previous: number | boolean | null;
  results: T[];
}
export interface Option { id: string; name: string }
export interface Activity {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  outcome: string;
  created_at: string;
}
export interface Dashboard {
  counts: Partial<Record<"patients" | "doctors" | "supervisors" | "assignments", number>>;
  specializations: Option[];
  recent_activity: Activity[];
}
export const roleName: Record<Role, string> = {
  super_admin: "Super Admin", supervisor: "Supervisor", doctor: "Doctor", patient: "Patient",
};
