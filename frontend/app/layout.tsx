import type { Metadata } from "next";
import { connection } from "next/server";
import "@fontsource-variable/dm-sans";
import "@fontsource/instrument-serif/400.css";
import "./styles.css";

export const metadata: Metadata = {
  title: { default: "Medora Healthcare", template: "%s · Medora Healthcare" },
  description: "A healthcare coordination workspace for patients and their care teams.",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  await connection();
  return <html lang="en"><body>{children}</body></html>;
}
