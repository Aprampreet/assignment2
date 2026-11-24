"use client";
import { useEffect, useRef, useState } from "react";
import { MessageCircle, Send, RotateCcw, Trash2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Role } from "@/lib/types";
import { Modal } from "./ui";

const suggestions: Record<Role, string[]> = {
  super_admin: ["How many active supervisors are there?", "How do I approve requests?", "How do I create a supervisor?"],
  supervisor: ["How many patients do I manage?", "How do I assign a doctor?", "How do I end an assignment?"],
  doctor: ["How many assigned patients do I have?", "How do I find assigned patients?", "How do I edit my profile?"],
  patient: ["How do I find my assigned doctors?", "How do I use the directory?", "How do I change my password?"],
};
type Exchange = { question: string; reply: string; source: string };

export function Assistant({ role }: { role: Role }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<Exchange[]>([]);
  const bottom = useRef<HTMLDivElement>(null);
  const chat = useMutation({
    mutationFn: (question: string) => api<{ reply: string; source: string }>("v1/assistant/chat", "POST", { message: question }),
    onSuccess: ({ reply, source }, question) => {
      setHistory((previous) => [...previous.slice(-19), { question, reply, source }]);
      setMessage("");
    },
  });
  useEffect(() => { if (open) bottom.current?.scrollIntoView({ block: "end", behavior: "smooth" }); }, [history, open]);
  function send(question: string) { if (question.trim() && !chat.isPending) chat.mutate(question.trim()); }
  return <>
    <button className="chat-launcher" onClick={() => setOpen(true)} aria-expanded={open} aria-label="Open workspace assistant"><MessageCircle size={19} /><span>Ask Medora</span></button>
    {open && <div className="assistant-wrap"><Modal title="Ask Medora" close={() => setOpen(false)}>
      <div className="assistant-intro"><span className="assistant-mark"><MessageCircle size={19} /></span><div><strong>Workspace assistant</strong><p>Answers about your workspace and the records you can access.</p></div></div>
      <div className="assistant-tools"><span>Conversation stays in this browser tab</span><button className="text-button" type="button" disabled={!history.length || chat.isPending} onClick={() => setHistory([])}><Trash2 size={15} /> Clear</button></div>
      <div className="chat-history" aria-live="polite" aria-label="Conversation">
        {!history.length && <div className="chat-welcome"><strong>What can I help you find?</strong><p>Choose a question or type your own. Please leave personal and clinical details out of chat.</p></div>}
        {history.map((entry, i) => <div className="chat-exchange" key={i}><p className="chat-question">{entry.question}</p><p className="chat-answer">{entry.reply}</p><small>{entry.source === "workspace" ? "From your workspace" : entry.source === "groq" ? "AI-assisted help" : "Platform help"}</small></div>)}
        {chat.isPending && <p className="chat-loading" role="status">Checking your workspace…</p>}
        <div ref={bottom} />
      </div>
      <div className="chat-suggestions" aria-label="Suggested questions">{suggestions[role].map((question) => <button type="button" key={question} onClick={() => send(question)} disabled={chat.isPending}>{question}</button>)}</div>
      {chat.isError && <p className="error chat-error" role="alert">{chat.error.message} <button className="text-button" onClick={() => chat.variables && send(chat.variables)}><RotateCcw size={14} /> Retry</button></p>}
      <form className="chat-form" onSubmit={(event) => { event.preventDefault(); send(message); }}>
        <label className="sr-only" htmlFor="assistant-message">Your workspace question</label><input id="assistant-message" placeholder="Ask about your workspace" maxLength={500} value={message} onChange={(event) => setMessage(event.target.value)} />
        <button className="button" aria-label="Send question" disabled={chat.isPending || !message.trim()}><Send size={17} /></button>
      </form>
    </Modal></div>}
  </>;
}
