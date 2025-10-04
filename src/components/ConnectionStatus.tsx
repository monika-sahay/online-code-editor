"use client";

import { useEffect, useState } from "react";

type Ping = { ok: boolean; url: string; error?: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
const FRONTEND_URL = process.env.NEXT_PUBLIC_FRONTEND_URL || "";
const MODE = (process.env.NEXT_PUBLIC_API_MODE || "queue").toLowerCase();

const endpoint = MODE === "queue" ? "/submit" : "/execute";

export default function ConnectionStatus() {
  const [api, setApi] = useState<Ping>({ ok: false, url: `${API_URL}` });
  const [front, setFront] = useState<Ping>({
    ok: true,
    url:
      FRONTEND_URL ||
      (typeof window !== "undefined" ? window.location.origin : ""),
  });

  useEffect(() => {
    let abort = new AbortController();
    (async () => {
      try {
        const r = await fetch(`${API_URL}/`, {
          signal: abort.signal,
          cache: "no-store",
        });
        setApi({ ok: r.ok, url: `${API_URL}${endpoint}` });
      } catch (e: any) {
        setApi({
          ok: false,
          url: `${API_URL}${endpoint}`,
          error: String(e?.message || e),
        });
      }
    })();
    return () => abort.abort();
  }, []);

  return (
    <div className="mt-4 rounded-xl border p-4 text-sm">
      <div className="font-semibold mb-2">Connection Status</div>

      <Row label="Backend API" value={`${api.url}`} ok={api.ok} />
      <Row label="Frontend" value={front.url} ok={true} />

      <p className="mt-2 text-xs text-muted-foreground">
        {MODE === "queue"
          ? "Using queued execution: POST /submit, then poll /status/:id and GET /result/:id."
          : "Using synchronous execution: POST /execute."}
      </p>
    </div>
  );
}

function Row({
  label,
  value,
  ok,
}: {
  label: string;
  value: string;
  ok: boolean;
}) {
  return (
    <div className="flex items-center gap-2 py-1">
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          ok ? "bg-green-500" : "bg-red-500"
        }`}
      />
      <span className="min-w-[110px] text-muted-foreground">{label}:</span>
      <code className="break-all">{value}</code>
    </div>
  );
}
