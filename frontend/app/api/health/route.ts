import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const headers = { "Cache-Control": "no-store" };

export async function GET() {
  const origin = process.env.DJANGO_API_ORIGIN;
  if (!origin) return NextResponse.json({ status: "unavailable" }, { status: 503, headers });

  try {
    const response = await fetch(new URL("/health/", origin), {
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(90000),
    });
    if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) {
      return NextResponse.json({ status: "unavailable" }, { status: 503, headers });
    }
    const payload = await response.json();
    if (payload?.status !== "ok") return NextResponse.json({ status: "unavailable" }, { status: 503, headers });
    return NextResponse.json({ status: "ok" }, { headers });
  } catch {
    return NextResponse.json({ status: "unavailable" }, { status: 503, headers });
  }
}
