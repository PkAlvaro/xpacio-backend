const BASE_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

// Access token in memory only — never in localStorage/sessionStorage.
// Refresh token lives in an httpOnly cookie set by the server (not accessible to JS).
let _accessToken: string | null = null;
let _refreshing: Promise<string | null> | null = null;

export function getAccessToken(): string | null {
  return _accessToken;
}

export function setTokens(access: string): void {
  _accessToken = access;
}

export function clearTokens(): void {
  _accessToken = null;
}

function refreshAccessToken(): Promise<string | null> {
  // Deduplicate concurrent refresh calls
  if (_refreshing) return _refreshing;

  _refreshing = fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  })
    .then(async (res) => {
      if (!res.ok) { clearTokens(); return null; }
      const { data } = await res.json();
      _accessToken = data.access_token;
      return data.access_token as string;
    })
    .catch(() => { clearTokens(); return null; })
    .finally(() => { _refreshing = null; });

  return _refreshing;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (_accessToken) headers["Authorization"] = `Bearer ${_accessToken}`;

  let res = await fetch(url, { ...options, headers, credentials: "include" });

  if (res.status === 401) {
    // Recover session: try refresh via httpOnly cookie (works after page reload too)
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(url, { ...options, headers, credentials: "include" });
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new ApiError(res.status, body.error ?? "Error desconocido", body);
  }

  return res.json();
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown
  ) {
    super(message);
  }
}
