"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { api, ApiError } from "@/lib/api";
import { Brand } from "./brand";

type Portal = "patient" | "doctor" | "supervisor";
type Fields = { name: string; email: string; password: string; specialization_slug: string; registration_number: string };

export function AuthForm({ register: create }: { register?: boolean }) {
  const router = useRouter();
  const [portal, setPortal] = useState<Portal>("patient");
  const [visible, setVisible] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<Fields>();

  async function submit(values: Fields) {
    try {
      if (create) {
        const body: Record<string, string> = { name: values.name, email: values.email, password: values.password, role: portal };
        if (portal === "doctor") {
          body.specialization_slug = values.specialization_slug;
          body.registration_number = values.registration_number;
        }
        await api("auth/register", "POST", body);
        if (portal !== "patient") { setSubmitted(true); return; }
      }
      await api("auth/login", "POST", { email: values.email, password: values.password, portal });
      router.replace("/workspace");
    } catch (error) {
      if (error instanceof ApiError) {
        for (const field of ["name", "email", "password", "specialization_slug", "registration_number"] as const) {
          if (error.fields[field]) setError(field, { message: [error.fields[field]].flat().join(" ") });
        }
      }
      setError("root", { message: error instanceof Error ? error.message : "Please try again." });
    }
  }

  return <main className="auth-layout">
    <aside><Brand /><p>Make it easier to stay connected to your care team.</p><Link href="/">Return to Medora Healthcare</Link></aside>
    <section className="auth-main"><div className="auth-form">
      {submitted ? <><h1>Request received</h1><p>An administrator will review your {portal} registration. You can sign in after approval.</p><Link href="/login">Return to sign in</Link></> : <>
        <h1>{create ? "Create an account" : "Sign in to Medora"}</h1>
        <p>{create ? "Choose your account type. Doctor and supervisor requests require administrator approval." : "Choose your workspace and enter your credentials."}</p>
        <div className="portal-options" role="group" aria-label="Account type">{(["patient", "doctor", "supervisor"] as Portal[]).map((option) => <button type="button" key={option} className={portal === option ? "portal-selected" : ""} onClick={() => setPortal(option)} aria-pressed={portal === option}>{option === "supervisor" && !create ? "Supervisor / Admin" : option[0].toUpperCase() + option.slice(1)}</button>)}</div>
        <form onSubmit={handleSubmit(submit)} noValidate>
          {create && <label>Full name<input autoComplete="name" {...register("name", { required: true, maxLength: 150 })} aria-invalid={!!errors.name} /><small>{errors.name?.message}</small></label>}
          <label>Email address<input type="email" autoComplete="email" {...register("email", { required: true })} aria-invalid={!!errors.email} /><small>{errors.email?.message}</small></label>
          <label htmlFor="auth-password">Password</label><div className="password-input"><input id="auth-password" type={visible ? "text" : "password"} autoComplete={create ? "new-password" : "current-password"} {...register("password", { required: true, minLength: create ? 12 : 1 })} aria-invalid={!!errors.password} /><button type="button" className="text-button" onClick={() => setVisible(!visible)}>{visible ? "Hide" : "Show"}</button></div>
          {create && portal === "doctor" && <><label>Specialization<input {...register("specialization_slug", { required: true })} placeholder="e.g. General Medicine" maxLength={100} /><small>{errors.specialization_slug?.message}</small></label><label>Registration number<input {...register("registration_number", { required: true })} maxLength={40} /><small>{errors.registration_number?.message}</small></label></>}
          {errors.root && <p role="alert" className="error">{errors.root.message}</p>}
          <button className="button full" disabled={isSubmitting}>{isSubmitting ? "Please wait…" : create ? portal === "patient" ? "Create account" : "Send approval request" : "Sign in"}</button>
        </form>
        <p>{create ? "Already have an account? " : "New to Medora? "}<Link href={create ? "/login" : "/register"}>{create ? "Sign in" : "Create an account"}</Link></p>
      </>}
    </div></section>
  </main>;
}
