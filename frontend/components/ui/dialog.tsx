"use client";

import * as Primitive from "@radix-ui/react-dialog";
import type { ComponentProps } from "react";
import { X } from "lucide-react";

export const Dialog = Primitive.Root;
export const DialogTitle = Primitive.Title;

export function DialogContent({ children, ...props }: ComponentProps<typeof Primitive.Content>) {
  return <Primitive.Portal>
    <Primitive.Overlay data-slot="dialog-overlay" className="dialog-overlay" />
    <Primitive.Content data-slot="dialog-content" className="dialog" {...props}>{children}</Primitive.Content>
  </Primitive.Portal>;
}

export function DialogClose() {
  return <Primitive.Close data-slot="dialog-close" className="icon-button" aria-label="Close"><X size={20} /></Primitive.Close>;
}
