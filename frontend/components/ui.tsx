"use client";

import { useRef, type ReactNode } from "react";
import { Dialog, DialogClose, DialogContent, DialogTitle } from "./ui/dialog";

export function Modal({ title, children, close }: { title: string; children: ReactNode; close: () => void }) {
  const opener = useRef<HTMLElement | null>(null);
  return <Dialog open onOpenChange={(open) => { if (!open) close(); }}>
    <DialogContent aria-describedby={undefined} onOpenAutoFocus={() => {
      if (document.activeElement instanceof HTMLElement) opener.current = document.activeElement;
    }} onCloseAutoFocus={(event) => {
      if (opener.current?.isConnected) { event.preventDefault(); opener.current.focus(); }
    }}>
      <div className="dialog-title"><DialogTitle>{title}</DialogTitle><DialogClose /></div>
      {children}
    </DialogContent>
  </Dialog>;
}
