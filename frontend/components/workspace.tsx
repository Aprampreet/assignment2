"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { QueryClient, QueryClientProvider, useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Activity as ActivityIcon, ChevronDown, ClipboardList, HeartPulse, LayoutDashboard, Menu, Plus, Search, Stethoscope, UserRound, UsersRound } from "lucide-react";
import { toast, Toaster } from "sonner";
import { api, ApiError } from "@/lib/api";
import { roleName, type Activity, type Dashboard, type Identity, type Item, type Page, type Role } from "@/lib/types";
import { Assistant } from "./assistant";
import { Brand } from "./brand";
import { PasswordForm, profileFields, RecordForm, type Resource } from "./record-form";
import { Modal } from "./ui";

type Tab = "overview" | "patients" | "doctors" | "directory" | "mappings" | "users" | "supervisors" | "audit" | "profile";
const labels: Record<Tab, string> = {
  overview: "Overview", patients: "Patients", doctors: "Managed doctors", directory: "Doctor directory",
  mappings: "Assignments", users: "Accounts", supervisors: "Supervisors", audit: "Audit log", profile: "My profile",
};
const navigation: Record<Role, Tab[]> = {
  super_admin: ["overview", "supervisors", "users", "patients", "doctors", "directory", "mappings", "audit"],
  supervisor: ["overview", "patients", "doctors", "directory", "mappings"],
  doctor: ["overview", "patients", "directory", "profile"],
  patient: ["overview", "profile", "mappings", "directory"],
};
const icons = {
  overview: LayoutDashboard, patients: HeartPulse, doctors: Stethoscope, directory: Stethoscope,
  mappings: ClipboardList, users: UsersRound, supervisors: UsersRound, audit: ActivityIcon, profile: UserRound,
};
const countLabel = {
  patients: "Active patients", doctors: "Active doctors", supervisors: "Active supervisors", assignments: "Active assignments",
};
const formatDate = (value: string) => new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
const initials = (value: string) => value.trim().split(/\s+/).slice(0, 2).map((name) => name[0]).join("").toUpperCase();
const readable = (value: string) => value.replaceAll("_", " ").replace(/^./, (first) => first.toUpperCase());
const scoped = (me: Identity, key: string) => [me.id, me.role, key];

function sectionTitle(me: Identity, tab: Tab) {
  if (tab === "mappings" && me.role === "patient") return "My care team";
  if (tab === "patients" && me.role === "doctor") return "Assigned patients";
  if (tab === "doctors" && me.role === "super_admin") return "Doctor management";
  return labels[tab];
}

export function Workspace() {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: {
    staleTime: 15000, retry: (attempt, error) => attempt < 1 && (!(error instanceof ApiError) || error.status >= 500),
  } } }));
  return <QueryClientProvider client={client}><Shell /><Toaster position="top-right" /></QueryClientProvider>;
}

function Shell() {
  const router = useRouter();
  const client = useQueryClient();
  const [tab, setTab] = useState<Tab>("overview");
  const [menu, setMenu] = useState(false);
  const [password, setPassword] = useState(false);
  const me = useQuery({ queryKey: ["identity"], queryFn: () => api<Identity>("auth/me") });

  useEffect(() => {
    const ended = () => { client.clear(); router.replace("/login"); };
    window.addEventListener("medora-session-ended", ended);
    const channel = typeof BroadcastChannel === "undefined" ? undefined : new BroadcastChannel("medora-account-changed");
    if (channel) channel.onmessage = ended;
    return () => {
      window.removeEventListener("medora-session-ended", ended);
      channel?.close();
    };
  }, [client, router]);

  function signedOut() { client.clear(); router.replace("/login"); }
  const logout = useMutation({
    mutationFn: () => api("auth/logout", "POST"),
    onSuccess: signedOut,
    onError: (error) => {
      if (error instanceof ApiError && error.status === 503) signedOut();
      else toast.error(error.message);
    },
  });
  if (me.isPending) return <main className="workspace-message">Opening your workspace…</main>;
  if (me.isError) return <main className="workspace-message"><p role="alert">{me.error.message}</p>
    <button className="button" onClick={() => me.refetch()}>Try again</button></main>;
  const identity = me.data;
  if (identity.must_change_password) return <main className="workspace-message">
    <Brand /><section className="panel"><h1>Change your temporary password</h1>
      <p>Set a new password to open your workspace. You’ll sign in again when it’s saved.</p>
      <PasswordForm id={identity.id} done={signedOut} />
      <button className="text-button" onClick={() => logout.mutate()} disabled={logout.isPending}>Sign out</button>
    </section></main>;

  return <div className="workspace-layout">
    <aside className={`sidebar ${menu ? "sidebar-open" : ""}`} id="workspace-navigation">
      <Brand workspace />
      <nav aria-label="Workspace navigation">{navigation[identity.role].map((item) => {
        const Icon = icons[item];
        return <button key={item} className={item === tab ? "nav-active" : ""} aria-current={item === tab ? "page" : undefined}
          onClick={() => { setTab(item); setMenu(false); }}><Icon size={19} />{sectionTitle(identity, item)}</button>;
      })}</nav>
      <div className="sidebar-bottom">Medora workspace</div>
    </aside>
    <div className="workspace-main">
      <header className="workspace-header">
        <div className="crumb"><button className="icon-button menu-toggle" aria-label="Toggle navigation" aria-expanded={menu} aria-controls="workspace-navigation" onClick={() => setMenu(!menu)}><Menu size={22} /></button>
          <span>Workspace</span><span aria-hidden="true">/</span><strong>{sectionTitle(identity, tab)}</strong></div>
        <details className="account-menu"><summary><span className="avatar">{initials(identity.name)}</span><span className="account-name">{identity.name}<small>{roleName[identity.role]}</small></span><ChevronDown size={16} /></summary>
          <div><button onClick={() => setPassword(true)}>Change password</button><button disabled={logout.isPending} onClick={() => logout.mutate()}>{logout.isPending ? "Signing out…" : "Sign out"}</button></div></details>
      </header>
      <main className="workspace-content"><WorkspaceBody key={`${identity.id}:${tab}`} me={identity} tab={tab} go={setTab} /></main>
    </div>
    {password && <Modal title="Change password" close={() => setPassword(false)}><PasswordForm id={identity.id} done={signedOut} /></Modal>}
    <Assistant key={identity.id} role={identity.role} />
  </div>;
}

function WorkspaceBody({ me, tab, go }: { me: Identity; tab: Tab; go: (tab: Tab) => void }) {
  const overview = useQuery({ queryKey: scoped(me, "dashboard"), queryFn: () => api<Dashboard>("v1/dashboard") });
  if (overview.isPending) return <p role="status">Loading workspace…</p>;
  if (overview.isError) return <FetchError error={overview.error} retry={() => overview.refetch()} />;
  const title = sectionTitle(me, tab);
  return <>
    <div className="page-heading"><h1>{tab === "overview" ? `Welcome, ${me.name.split(" ")[0]}` : title}</h1>
      <p>{tab === "overview" ? `${roleName[me.role]} workspace` : ({
        patients: "Review the patient records available to you.", doctors: "Review and maintain doctor profiles.",
        directory: "Browse doctors by name or specialization.", mappings: me.role === "patient" ? "Doctors currently assigned to you." : "Review patient and doctor assignments.",
        users: "Manage account access and registration approvals.", supervisors: "Review supervisors and create an account.", audit: "Review recorded account and profile activity.",
        profile: "Review your profile and keep your information up to date.",
      } as Partial<Record<Tab, string>>)[tab]}</p></div>
    {tab === "overview" ? <Overview me={me} data={overview.data} go={go} /> :
      tab === "audit" ? <AuditTable me={me} /> :
      tab === "profile" ? <MyProfile me={me} dashboard={overview.data} /> :
      <Records me={me} tab={tab} dashboard={overview.data} />}
  </>;
}

function Overview({ me, data, go }: { me: Identity; data: Dashboard; go: (tab: Tab) => void }) {
  const quick = navigation[me.role].filter((tab) => tab !== "overview").slice(0, 4);
  const introduction: Record<Role, string> = {
    super_admin: "Review access, coordinate your supervisors and keep the whole organization moving.",
    supervisor: "Your team, patient records and doctor assignments are all within reach.",
    doctor: "Stay close to the patients in your care and keep your profile current.",
    patient: "Your details, doctor directory and care team are here whenever you need them.",
  };
  return <>
    <section className="overview-intro"><div><span className="overview-intro-mark"><HeartPulse size={22} /></span><h2>Your care workspace</h2><p>{introduction[me.role]}</p></div><span className="overview-role">{roleName[me.role]}</span></section>
    <div className="count-grid">{Object.entries(data.counts).map(([key, count]) => <div className="count-card" key={key}>
      <span>{me.role === "doctor" && key === "patients" ? "Assigned patients" : me.role === "patient" && key === "assignments" ? "Assigned doctors" : countLabel[key as keyof typeof countLabel]}</span>
      <strong>{count}</strong></div>)}</div>
    <section className="panel overview-panel"><div className="section-heading"><div><h2>Continue your work</h2><p>Open the areas you use most.</p></div></div><div className="quick-links">{quick.map((tab) => {
      const Icon = icons[tab];
      return <button className="button secondary" key={tab} onClick={() => go(tab)}><Icon size={18} />{sectionTitle(me, tab)}</button>;
    })}</div></section>
    {(me.role === "super_admin" || me.role === "supervisor") && <section className="panel overview-panel"><h2>Recent activity</h2><ActivityRows events={data.recent_activity} /></section>}
  </>;
}

function FetchError({ error, retry }: { error: Error; retry: () => void }) {
  return <div className="panel" role="alert"><p>{error.message}</p><button className="button secondary" onClick={retry}>Try again</button></div>;
}

function useSearch() {
  const [raw, setRaw] = useState("");
  const [search, setSearch] = useState("");
  useEffect(() => {
    const handle = setTimeout(() => setSearch(raw.trim()), 280);
    return () => clearTimeout(handle);
  }, [raw]);
  return { raw, setRaw, search };
}

function Pager({ page, data, setPage }: { page: number; data: Page<unknown>; setPage: (p: number) => void }) {
  return <div className="pager"><span>{data.count} {data.count === 1 ? "record" : "records"} · Page {page}</span>
    <div className="actions"><button className="button secondary" disabled={!data.previous} onClick={() => setPage(page - 1)}>Previous</button>
      <button className="button secondary" disabled={!data.next} onClick={() => setPage(page + 1)}>Next</button></div></div>;
}

function ActivityRows({ events }: { events: Activity[] }) {
  if (!events.length) return <p className="empty">No activity to show.</p>;
  return <div className="table-scroll"><table><thead><tr><th>Action</th><th>Resource</th><th>Outcome</th><th>Date</th></tr></thead>
    <tbody>{events.map((event) => <tr key={event.id}><td>{readable(event.action)}</td><td>{readable(event.resource_type)}</td>
      <td>{readable(event.outcome)}</td><td>{formatDate(event.created_at)}</td></tr>)}</tbody></table></div>;
}

function AuditTable({ me }: { me: Identity }) {
  const [page, setPage] = useState(1);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [sort, setSort] = useState("recent");
  const params = new URLSearchParams({ page: String(page), sort });
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const query = useQuery({ queryKey: [...scoped(me, "audit"), params.toString()], queryFn: () => api<Page<Activity>>(`v1/audit-logs?${params}`) });
  return <section className="panel data-panel">
    <div className="toolbar"><label>From<input type="date" value={start} onChange={(e) => { setStart(e.target.value); setPage(1); }} /></label>
      <label>Through<input type="date" value={end} onChange={(e) => { setEnd(e.target.value); setPage(1); }} /></label>
      <label>Sort<select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }}><option value="recent">Newest</option><option value="oldest">Oldest</option></select></label></div>
    {query.isPending ? <p className="empty" role="status">Loading activity…</p> :
      query.isError ? <FetchError error={query.error} retry={() => query.refetch()} /> :
      <><ActivityRows events={query.data.results} /><Pager page={page} data={query.data} setPage={setPage} /></>}
  </section>;
}

type RecordTab = Exclude<Tab, "overview" | "audit" | "profile">;
function Records({ me, tab, dashboard }: { me: Identity; tab: RecordTab; dashboard: Dashboard }) {
  const management = me.role === "super_admin" || me.role === "supervisor";
  const isDoctor = tab === "doctors" || tab === "directory";
  const resource = tab === "directory" ? "doctors" : tab === "supervisors" ? "users" : tab;
  const queryResource = tab === "mappings" && me.role === "patient" ? `mappings/${me.profile_id}` : resource;
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("recent");
  const [specialty, setSpecialty] = useState("");
  const [status, setStatus] = useState(tab === "directory" && me.role === "super_admin" ? "true" : "");
  const [roleFilter, setRoleFilter] = useState("");
  const [selected, setSelected] = useState<Item>();
  const [create, setCreate] = useState(false);
  const [confirm, setConfirm] = useState<Item>();
  const { raw, setRaw, search } = useSearch();
  const client = useQueryClient();
  const params = new URLSearchParams({ page: String(page), sort });
  if (search) params.set("search", search);
  if (specialty) params.set("specialization", specialty);
  if (status) params.set("active", status);
  if (tab === "supervisors") params.set("role", "supervisor");
  if (tab === "users" && roleFilter) params.set("role", roleFilter);
  if (tab === "doctors" && me.role === "supervisor") params.set("managed", "true");
  const query = useQuery({ queryKey: [...scoped(me, tab), params.toString()], queryFn: () => api<Page<Item>>(`${queryResource}?${params}`) });
  const refresh = () => { setPage(1); return client.invalidateQueries({ queryKey: [me.id, me.role] }); };
  const action = useMutation({
    mutationFn: async (item: Item) => {
      if (resource === "users") await api(`users/${item.id}`, "PATCH", item.approval_pending ? { is_active: true, approval_pending: false } : { is_active: !item.is_active });
      else await api(`${resource}/${item.id}`, "DELETE");
    },
    onSuccess: () => { setConfirm(undefined); void refresh(); toast.success(tab === "mappings" ? "Assignment ended." : resource === "users" ? "Account updated." : "Record archived."); },
  });
  const add = tab === "mappings" ? "Assign doctor" : tab === "users" ? "Add account" : tab === "supervisors" ? "Add supervisor" : tab === "patients" ? "Add patient" : "Add doctor";
  const statusFilter = (me.role === "super_admin" && tab !== "directory") || (management && tab === "mappings");
  return <>
    <section className="panel data-panel">
      <div className="toolbar">
        <label className="search-label"><span>Search</span><div className="search-input"><Search size={17} /><input value={raw} placeholder={resource === "users" ? "Name or email" : "Search by name"} onChange={(e) => { setRaw(e.target.value); setPage(1); }} /></div></label>
        {isDoctor && <label>Specialization<select value={specialty} onChange={(e) => { setSpecialty(e.target.value); setPage(1); }}>
          <option value="">All specializations</option>{dashboard.specializations.map(({ id, name }) => <option key={id} value={id}>{name}</option>)}</select></label>}
        {tab === "users" && <label>Role<select value={roleFilter} onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}>
          <option value="">All roles</option>{Object.entries(roleName).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select></label>}
        {statusFilter && <label>Status<select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">All statuses</option><option value="true">Active</option><option value="false">{tab === "mappings" ? "Ended" : "Inactive"}</option></select></label>}
        <label>Sort<select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }}>
          <option value="recent">Newest</option>{resource !== "users" && <option value="oldest">Oldest</option>}
          {tab !== "mappings" && <><option value="name">Name A–Z</option><option value="-name">Name Z–A</option></>}</select></label>
        {management && tab !== "directory" && <button className="button add-button" onClick={() => setCreate(true)}><Plus size={17} />{add}</button>}
      </div>
      {query.isPending ? <p className="empty" role="status">Loading records…</p> : query.isError ? <FetchError error={query.error} retry={() => query.refetch()} /> :
        <>{!query.data.results.length ? <p className="empty">No records match your filters.</p> :
          tab === "mappings" && me.role === "patient" ? <div className="doctor-grid">{query.data.results.map((item) => <article key={item.id}>
            <span className="avatar">{initials(String(item.doctor_name))}</span><h2>{item.doctor_name}</h2><p>{item.doctor_specialization}</p></article>)}</div> :
          <div className="table-scroll"><table><thead><tr>
            {tab === "mappings" ? <><th>Patient</th><th>Doctor</th><th>Assigned</th><th>Status</th></> :
              <><th>Name</th>{isDoctor ? <><th>Specialization</th><th>Experience</th></> :
                resource === "users" ? <><th>Email</th><th>Role</th><th>Status</th></> : <th>Blood group</th>}</>}
            <th><span className="sr-only">Actions</span></th>
          </tr></thead><tbody>{query.data.results.map((item) => <tr key={item.id}>
            {tab === "mappings" ? <><td>{item.patient_name}</td><td>{item.doctor_name}</td><td>{formatDate(String(item.assigned_at))}</td>
              <td>{item.ended_at ? "Ended" : "Active"}</td></> :
              <><td><strong>{item.name}</strong></td>{isDoctor ? <><td>{item.specialization_name}</td><td>{item.years_of_experience} years</td></> :
                resource === "users" ? <><td>{item.email}</td><td>{roleName[item.role as Role]}</td><td>{item.approval_pending ? "Pending approval" : item.is_archived ? "Archived" : item.is_active ? "Active" : "Inactive"}</td></> : <td>{item.blood_group || "—"}</td>}</>}
            <td className="row-actions">
              {tab !== "mappings" && resource !== "users" && <button className="text-button" onClick={() => setSelected(item)}>View</button>}
              {tab === "mappings" && management && !item.ended_at && <button className="text-button" onClick={() => { action.reset(); setConfirm(item); }}>End assignment</button>}
              {resource === "users" && item.role !== "super_admin" && <><button className="text-button" onClick={() => setSelected(item)}>Edit name</button>{!item.is_archived && <button className="text-button" onClick={() => { action.reset(); setConfirm(item); }}>{item.approval_pending ? "Approve" : item.is_active ? "Suspend" : "Reactivate"}</button>}</>}
            </td></tr>)}</tbody></table></div>}
          <Pager page={page} data={query.data} setPage={setPage} /></>}
    </section>
    {create && (resource === "mappings" ? <AssignmentForm me={me} close={() => setCreate(false)} done={refresh} /> :
      <ProfileDialog me={me} resource={resource} dashboard={dashboard} supervisorOnly={tab === "supervisors"} close={() => setCreate(false)} done={refresh} />)}
    {selected && (resource === "users" ?
      <Modal title={String(selected.name)} close={() => setSelected(undefined)}><RecordForm initial={selected} label="Save name" fields={[{ key: "name", label: "Full name", required: true, max: 150 }]}
        submit={async (body) => { await api(`users/${selected.id}`, "PATCH", body); setSelected(undefined); await refresh(); toast.success("Account updated."); }} /></Modal> :
      resource !== "mappings" && <ProfileDialog me={me} resource={resource} id={selected.id} directory={tab === "directory"} dashboard={dashboard}
        close={() => setSelected(undefined)} done={refresh} />)}
    {confirm && <Modal title={tab === "mappings" ? "End assignment?" : confirm.approval_pending ? "Approve registration?" : confirm.is_active ? "Suspend account?" : "Reactivate account?"}
      close={() => { if (!action.isPending) setConfirm(undefined); }}>
      <p>{tab === "mappings" ? `End the assignment between ${confirm.patient_name} and ${confirm.doctor_name}?` : `Change workspace access for ${confirm.name}?`}</p>
      {action.isError && <p role="alert" className="error">{action.error.message}</p>}
      <div className="form-actions"><button className="button secondary" disabled={action.isPending} onClick={() => setConfirm(undefined)}>Cancel</button>
        <button className="button danger" disabled={action.isPending} onClick={() => action.mutate(confirm)}>{action.isPending ? "Saving…" : "Confirm"}</button></div>
    </Modal>}
  </>;
}

function AssignmentForm({ me, close, done }: { me: Identity; close: () => void; done: () => Promise<unknown> }) {
  const [patient, setPatient] = useState<Item>();
  const [doctor, setDoctor] = useState<Item>();
  const [reason, setReason] = useState("");
  const client = useQueryClient();
  const data = useMutation({
    mutationFn: () => api("mappings", "POST", { patient_id: patient?.id, doctor_id: doctor?.id, assignment_reason: reason }),
    onSuccess: () => { close(); void done(); toast.success("Doctor assigned."); },
  });
  const existing = useQuery({
    queryKey: [...scoped(me, "assignment-check"), patient?.id, doctor?.id],
    queryFn: () => api<Page<Item>>(`mappings/${patient?.id}?active=true&doctor_id=${doctor?.id}&page_size=1`),
    enabled: !!patient && !!doctor,
  });
  const duplicate = !!existing.data?.count;
  return <Modal title="Assign doctor" close={() => { if (!data.isPending) close(); }}>
    <form className="record-form" onSubmit={(e) => { e.preventDefault(); if (patient && doctor && existing.isSuccess && !duplicate) data.mutate(); }}>
      <Picker me={me} resource="patients" label="Patient" value={patient} select={(item) => { setPatient(item); data.reset(); void client.invalidateQueries({ queryKey: scoped(me, "assignment-check") }); }} />
      <Picker me={me} resource="doctors" label="Doctor" value={doctor} select={(item) => { setDoctor(item); data.reset(); }} />
      <label>Assignment reason <small>(optional)</small><textarea value={reason} onChange={(e) => setReason(e.target.value)} maxLength={250} rows={2} /></label>
      {duplicate && <p role="alert" className="error">This doctor is already assigned to the patient.</p>}
      {existing.isError && <p className="error" role="alert">{existing.error.message} <button className="text-button" type="button" onClick={() => existing.refetch()}>Retry</button></p>}
      {data.isError && <p role="alert" className="error">{data.error.message}</p>}
      <div className="form-actions"><button className="button" disabled={!patient || !doctor || !existing.isSuccess || duplicate || data.isPending}>{data.isPending ? "Assigning…" : "Assign doctor"}</button></div>
    </form>
  </Modal>;
}

function Picker({ me, resource, label, value, select }: { me: Identity; resource: "patients" | "doctors"; label: string; value?: Item; select: (item?: Item) => void }) {
  const { raw, setRaw, search } = useSearch();
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), page_size: "6", sort: "name", search });
  if (resource === "patients") params.set("assignable", "true");
  else if (me.role === "super_admin") params.set("active", "true");
  const query = useQuery({
    queryKey: [...scoped(me, `pick-${resource}`), params.toString()],
    queryFn: () => api<Page<Item>>(`${resource}?${params}`),
    enabled: !value,
  });
  if (value) return <p className="picked"><strong>{label}</strong> {value.name} <button type="button" className="text-button" onClick={() => select(undefined)}>Change</button></p>;
  return <fieldset className="picker"><legend>{label}</legend>
    <label className="sr-only" htmlFor={`pick-${resource}`}>Search {resource}</label>
    <input id={`pick-${resource}`} placeholder={`Search ${resource}`} value={raw} onChange={(e) => { setRaw(e.target.value); setPage(1); }} />
    {query.isPending ? <p role="status">Loading…</p> : query.isError ? <p role="alert">{query.error.message} <button type="button" className="text-button" onClick={() => query.refetch()}>Retry</button></p> :
      <><div className="picker-results">{query.data.results.filter((item) => item.is_active !== false).map((item) => <button type="button" key={item.id} onClick={() => select(item)}>{item.name}</button>)}</div>
        {!query.data.results.length && <p>No records found.</p>}
        {(query.data.next || query.data.previous) && <div className="actions"><button type="button" className="text-button" disabled={!query.data.previous} onClick={() => setPage(page - 1)}>Previous</button>
          <button type="button" className="text-button" disabled={!query.data.next} onClick={() => setPage(page + 1)}>Next</button></div>}</>}
  </fieldset>;
}

const detailLabels: Record<string, string> = {
  email: "Email address", date_of_birth: "Date of birth", gender: "Gender", blood_group: "Blood group",
  phone: "Phone", address: "Address", allergies: "Allergies", medical_history: "Medical history", specialization_name: "Specialization",
  registration_number: "Registration number", qualifications: "Qualifications", years_of_experience: "Years of experience",
  biography: "Biography", professional_phone: "Professional phone", is_active: "Account status", archived_at: "Archived on",
};
function Details({ item, directory }: { item: Item; directory?: boolean }) {
  return <dl className="details-grid">{Object.entries(detailLabels).filter(([key]) =>
    key in item && (key !== "archived_at" || item[key]) &&
    (!directory || ["specialization_name", "qualifications", "years_of_experience", "biography"].includes(key)),
  ).map(([key, label]) => {
    const value = item[key];
    return <div key={key}><dt>{label}</dt><dd>{typeof value === "boolean" ? value ? "Active" : "Inactive" : key === "gender" && value ? readable(String(value)) : value ?? "—"}{value === "" && "—"}</dd></div>;
  })}</dl>;
}

function ProfileDialog({ me, resource, dashboard, id, directory, supervisorOnly, close, done }: {
  me: Identity; resource: Resource; dashboard: Dashboard; id?: string; directory?: boolean; supervisorOnly?: boolean;
  close: () => void; done: () => Promise<unknown>;
}) {
  const [edit, setEdit] = useState(!id);
  const [confirm, setConfirm] = useState(false);
  const result = useQuery({ queryKey: [...scoped(me, resource), "detail", id], queryFn: () => api<Item>(`${resource}/${id}`), enabled: !!id });
  const ownerSearch = useSearch();
  const owners = useQuery({
    queryKey: [...scoped(me, "owners"), ownerSearch.search],
    queryFn: () => api<Page<Item>>(`users?${new URLSearchParams({
      role: "supervisor", active: "true", page_size: "20", sort: "name", search: ownerSearch.search,
    })}`),
    enabled: me.role === "super_admin" && resource !== "users" && edit,
  });
  const archive = useMutation({
    mutationFn: () => api(`${resource}/${id}`, "DELETE"),
    onSuccess: () => { close(); void done(); toast.success("Record archived."); },
  });
  const item = result.data;
  const canManage = !directory && !item?.archived_at && (me.role === "super_admin" || (me.role === "supervisor" && item?.managed_by === me.id));
  const title = id ? String(item?.name ?? "Record details") : resource === "patients" ? "Add patient" : resource === "doctors" ? "Add doctor" : supervisorOnly ? "Add supervisor" : "Add account";
  const ownerOptions = (owners.data?.results ?? []).map((owner) => ({ id: owner.id, name: String(owner.name) }));
  if (item?.managed_by && !ownerOptions.some((option) => option.id === item.managed_by)) ownerOptions.push({ id: String(item.managed_by), name: "Current supervisor" });
  return <Modal title={title} close={() => { if (!archive.isPending) close(); }}>
    {id && result.isPending ? <p role="status">Loading record…</p> : result.isError ? <FetchError error={result.error} retry={() => result.refetch()} /> :
      confirm ? <><p>Archive {item?.name}? Their account will be deactivated and active assignments will end.</p>
        {archive.isError && <p className="error" role="alert">{archive.error.message}</p>}
        <div className="form-actions"><button className="button secondary" disabled={archive.isPending} onClick={() => setConfirm(false)}>Cancel</button>
          <button className="button danger" disabled={archive.isPending} onClick={() => archive.mutate()}>{archive.isPending ? "Archiving…" : "Archive record"}</button></div></> :
      edit ? <>{me.role === "super_admin" && resource !== "users" && <label>Find a supervisor
        <input value={ownerSearch.raw} placeholder="Search supervisor name" onChange={(e) => ownerSearch.setRaw(e.target.value)} />
        {owners.isFetching && <small role="status">Looking up supervisors…</small>}
        {owners.isError && <small role="alert">{owners.error.message} <button className="text-button" onClick={() => owners.refetch()}>Retry</button></small>}
      </label>}
        <RecordForm fields={profileFields(resource, me.role, !id, dashboard.specializations, ownerOptions).filter((field) => !supervisorOnly || field.key !== "role")} initial={item} label={id ? "Save changes" : "Create account"}
          submit={async (data) => { await api(id ? `${resource}/${id}` : resource, id ? "PUT" : "POST", supervisorOnly ? { ...data, role: "supervisor" } : data); close(); await done(); toast.success(id ? "Changes saved." : "Account created."); }} /></> :
      item && <><Details item={item} directory={directory} />{canManage && <div className="form-actions">
        <button className="button secondary" onClick={() => setConfirm(true)}>Archive</button><button className="button" onClick={() => setEdit(true)}>Edit profile</button></div>}</>}
  </Modal>;
}

function MyProfile({ me, dashboard }: { me: Identity; dashboard: Dashboard }) {
  const [edit, setEdit] = useState(false);
  const client = useQueryClient();
  const resource = me.role === "doctor" ? "doctors" : "patients";
  const path = `${resource}/${me.profile_id}`;
  const query = useQuery({ queryKey: [...scoped(me, resource), "own"], queryFn: () => api<Item>(path) });
  if (query.isPending) return <p role="status">Loading profile…</p>;
  if (query.isError) return <FetchError error={query.error} retry={() => query.refetch()} />;
  return <section className="panel profile-panel"><div className="profile-heading"><span className="avatar">{initials(String(query.data.name))}</span>
    <h2>{query.data.name}</h2><button className="button secondary" onClick={() => setEdit(true)}>Edit profile</button></div>
    <Details item={query.data} />
    {edit && <Modal title="Edit profile" close={() => setEdit(false)}><RecordForm fields={profileFields(resource, me.role, false, dashboard.specializations, [])}
      initial={query.data} label="Save changes" submit={async (data) => {
        await api(path, "PUT", data); setEdit(false); await client.invalidateQueries(); toast.success("Profile updated.");
      }} /></Modal>}
  </section>;
}
