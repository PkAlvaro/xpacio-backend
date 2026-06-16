import { useEffect, useState } from "react";
import { api, setTokens, setUser, clearAuth, getUser, getRole, isAuthenticated, StoredUser } from "@/lib/api";

interface TokenBundle {
  access_token: string;
  refresh_token: string;
}

export async function login(email: string, password: string): Promise<StoredUser> {
  const tokens = await api<TokenBundle>("/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
  setTokens(tokens.access_token, tokens.refresh_token);
  const me = await api<StoredUser>("/auth/me");
  setUser(me);
  return me;
}

export async function register(
  name: string,
  email: string,
  password: string,
  role: "client" | "provider" = "client",
): Promise<StoredUser> {
  const data = await api<{ user: StoredUser; tokens: TokenBundle }>("/auth/register", {
    method: "POST",
    body: { name, email, password, role },
    auth: false,
  });
  setTokens(data.tokens.access_token, data.tokens.refresh_token);
  setUser(data.user);
  return data.user;
}

export async function logout() {
  try {
    await api("/auth/logout", { method: "POST" });
  } catch {
    /* ignore */
  }
  clearAuth();
}

// Hook reactivo al estado de autenticación (escucha el evento global)
export function useAuth() {
  const [user, setU] = useState<StoredUser | null>(getUser());
  const [authed, setAuthed] = useState<boolean>(isAuthenticated());

  useEffect(() => {
    const handler = () => {
      setU(getUser());
      setAuthed(isAuthenticated());
    };
    window.addEventListener("xpacio-auth-change", handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("xpacio-auth-change", handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  return { user, isAuthenticated: authed, role: getRole(), logout };
}
