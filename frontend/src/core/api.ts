/** Typed API client — the only place that talks to the backend. */

export class ApiError extends Error {
  code: string
  status: number
  details?: unknown

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message)
    this.code = code
    this.status = status
    this.details = details
  }
}

/** API origin — works everywhere without rebuilds:
 *  • Web (vite proxy): set nothing — relative `/api/v1` goes through the dev server.
 *  • Android/Capacitor (https://localhost in a WebView): set `localStorage.karvantana.server`,
 *    e.g. http://192.168.1.20:8014 — the in-app Server Settings screen on Login.
 *  • Optional build default: VITE_API_ORIGIN in `.env` (picked up at build time).
 *  Same for `/media` product photos, so images load in the WebView too. */
export function apiOrigin(): string {
  try {
    return localStorage.getItem('karvantana.server') || import.meta.env.VITE_API_ORIGIN || ''
  } catch {
    return import.meta.env.VITE_API_ORIGIN || ''
  }
}

/** Prefix a backend-served path (e.g. /media/xxx.webp) with the server origin. */
export function serverUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path
  return `${apiOrigin()}${path}`
}

const BASE = '/api/v1'

/** Full URL for an API path, honoring the runtime-configurable server origin. */
function fullUrl(path: string): string {
  return `${apiOrigin()}${BASE}${path}`
}

let accessToken: string | null = null

export function setToken(token: string | null): void {
  accessToken = token
}

export function getToken(): string | null {
  return accessToken
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {}
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`
  if (init.body && !(init.body instanceof Blob) && !(init.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  let res: Response
  try {
    res = await fetch(fullUrl(path), { ...init, headers: { ...headers, ...(init.headers as Record<string, string>) } })
  } catch {
    // Browsers throw a bare TypeError ("Failed to fetch") for network failures —
    // translate it into guidance the user can act on.
    const onApp = !!apiOrigin()
    throw new ApiError(
      'NETWORK_ERROR',
      onApp
        ? `Cannot reach the KARVANTANA server at ${apiOrigin()}. Check that the backend is running and the Server address on the login screen is correct.`
        : 'Cannot reach the KARVANTANA server. Make sure the backend is running (uvicorn on port 8014) and try again.',
      0,
    )
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) {
    const err = (body as { error?: { code?: string; message?: string; details?: unknown } })?.error
    let message = err?.message ?? 'Something went wrong. Please try again.'
    const details = err?.details as { retry_after_seconds?: number } | undefined
    if (res.status === 429 && details?.retry_after_seconds) {
      message += ` Try again in ${details.retry_after_seconds}s.`
    }
    throw new ApiError(err?.code ?? 'REQUEST_FAILED', message, res.status, err?.details)
  }
  return body as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown, idempotencyKey?: string) =>
    request<T>(path, {
      method: 'POST',
      body: data === undefined ? undefined : JSON.stringify(data),
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
    }),
  patch: <T>(path: string, data: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, file: Blob, name: string) => {
    const form = new FormData()
    form.append('file', file, name)
    return request<T>(path, { method: 'POST', body: form })
  },
  /** WhatsApp simulator: send one inbound chat exchange (text/button/photo/voice). */
  waSend: <T>(fields: Record<string, string>, file?: { blob: Blob; name: string; kind: 'image' | 'audio' }) => {
    const form = new FormData()
    Object.entries(fields).forEach(([k, v]) => form.append(k, v))
    if (file) form.append(file.kind === 'image' ? 'image' : 'audio', file.blob, file.name)
    return request<T>(`${apiOrigin()}${BASE}/whatsapp/webhook`, { method: 'POST', body: form })
  },
  waThread: <T>() => request<T>(`${apiOrigin()}${BASE}/whatsapp/thread`),
  waSetPhone: <T>(phone: string) => request<T>(`${apiOrigin()}${BASE}/whatsapp/phone`, { method: 'POST', body: JSON.stringify({ phone }) }),
}
