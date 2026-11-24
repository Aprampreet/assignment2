import { Cross } from "lucide-react";
import Link from "next/link";

export function Brand({ workspace = false }: { workspace?: boolean }) {
  return <Link href={workspace ? "/workspace" : "/"} className="brand" aria-label="Medora Healthcare home">
    <span><Cross size={21} strokeWidth={2.7} /></span><strong>Medora</strong><small>Healthcare</small>
  </Link>;
}
