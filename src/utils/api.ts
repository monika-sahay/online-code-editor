// src/utils/api.ts
import type { ExecutionResult, Language } from "@/types/editor";

/** Read the API base from env; fall back to localhost in dev */
const BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  (process.env.NODE_ENV !== "production"
    ? "http://localhost:8001"
    : "https://online-code-editor-idoc.onrender.com");

/** Default timeout (ms) for network requests */
const DEFAULT_TIMEOUT = 15_000;

/** Typed API error carrying status + parsed body (if any) */
export class ApiError extends Error {
  status: number;
  body?: unknown;
  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

/* ---------- type guards (no `any`) ---------- */
function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

function bodyToMessage(body: unknown): string | null {
  if (typeof body === "string") return body;
  if (isRecord(body)) {
    const err = body.error;
    if (typeof err === "string") return err;
    const msg = body.message;
    if (typeof msg === "string") return msg;
  }
  return null;
}

function isAbortError(e: unknown): boolean {
  return (
    isRecord(e) &&
    typeof (e as { name?: unknown }).name === "string" &&
    (e as { name: string }).name === "AbortError"
  );
}

/* ---------- fetch wrapper with timeout + retry ---------- */
async function fetchJSON<T>(
  path: string,
  init: RequestInit & { timeoutMs?: number; retries?: number } = {}
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT, retries = 1, ...rest } = init;

  let lastErr: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(`${BASE}${path}`, {
        ...rest,
        signal: controller.signal,
        // Keep headers simple and typed; avoid spreading Headers objects
        headers: { "Content-Type": "application/json" },
      });

      clearTimeout(timer);

      const raw = await res.text();
      const isJson = raw.trim().startsWith("{") || raw.trim().startsWith("[");
      const data: unknown = isJson ? JSON.parse(raw) : raw;

      if (!res.ok) {
        const msg = bodyToMessage(data) ?? res.statusText;
        throw new ApiError(`API ${res.status}: ${msg}`, res.status, data);
      }
      return data as T;
    } catch (err) {
      clearTimeout(timer);

      // Do not retry typed HTTP errors
      if (err instanceof ApiError) throw err;

      // Retry only network/abort errors
      lastErr = err;
      if (attempt < retries) continue;

      if (isAbortError(err)) {
        throw new Error("Request timed out");
      }
      throw err instanceof Error ? err : new Error("Unknown network error");
    }
  }

  // Should be unreachable
  throw lastErr instanceof Error ? lastErr : new Error("Unknown error");
}

/** Execute code (Python/R) */
export async function runCode(
  code: string,
  language: Language
): Promise<ExecutionResult> {
  return fetchJSON<ExecutionResult>("/execute", {
    method: "POST",
    body: JSON.stringify({ code, language }),
    timeoutMs: 20_000,
    retries: 1,
  });
}

/** Ask backend for AI completion (short timeout) */
export async function aiComplete(
  code: string,
  cursorOffset: number
): Promise<string> {
  const resp = await fetchJSON<{ suggestion?: string }>("/ai-complete", {
    method: "POST",
    body: JSON.stringify({ code, cursorOffset }),
    timeoutMs: 6_000,
    retries: 0,
  });
  return typeof resp.suggestion === "string" ? resp.suggestion : "";
}
