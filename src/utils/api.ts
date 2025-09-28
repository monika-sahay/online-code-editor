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

/** A typed API error with status + response body (if any) */
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

/** fetch wrapper with JSON parsing, timeout, and small retry on network errors */
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
        headers: {
          "Content-Type": "application/json",
          ...(rest.headers || {}),
        },
      });
      clearTimeout(timer);

      const text = await res.text();
      const isJson = text.trim().startsWith("{") || text.trim().startsWith("[");
      const data = isJson ? (JSON.parse(text) as unknown) : text;

      if (!res.ok) {
        const msg =
          typeof data === "string"
            ? data
            : (data as any)?.error ?? res.statusText;
        throw new ApiError(`API ${res.status}: ${msg}`, res.status, data);
      }
      return data as T;
    } catch (err) {
      clearTimeout(timer);
      // Retry only on network/abort errors (not HTTP errors)
      if (err instanceof ApiError) throw err;
      lastErr = err;
      if (attempt < retries) continue;
      if ((err as any)?.name === "AbortError")
        throw new Error("Request timed out");
      throw err;
    }
  }
  // Should not reach
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
    timeoutMs: 20_000, // allow a bit longer than default
    retries: 1,
  });
}

/** Ask backend for AI completion (short timeout) */
export async function aiComplete(
  code: string,
  cursorOffset: number
): Promise<string> {
  const data = await fetchJSON<{ suggestion?: string }>("/ai-complete", {
    method: "POST",
    body: JSON.stringify({ code, cursorOffset }),
    timeoutMs: 6_000,
    retries: 0,
  });
  return data.suggestion ?? "";
}

// import type { ExecutionResult, Language } from "@/types/editor";

// const DEV = process.env.NODE_ENV !== "production";
// const BASE =
//   DEV ? "http://localhost:8001" : "https://online-code-editor-idoc.onrender.com";

// export async function runCode(code: string, language: Language): Promise<ExecutionResult> {
//   const res = await fetch(`${BASE}/execute`, {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify({ code, language }),
//   });
//   if (!res.ok) throw new Error(`HTTP ${res.status}`);
//   return (await res.json()) as ExecutionResult;
// }

// export async function aiComplete(code: string, cursorOffset: number): Promise<string> {
//   const res = await fetch(`${BASE}/ai-complete`, {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify({ code, cursorOffset }),
//   });
//   if (!res.ok) return "";
//   const data = (await res.json()) as { suggestion?: string };
//   return data.suggestion ?? "";
// }
