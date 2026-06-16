import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, setTokens, clearTokens } from "@/lib/api";
import type { ApiResponse, TokenResponse, UserResponse } from "@/types/api";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await apiRequest<ApiResponse<UserResponse>>("/auth/me");
      return res.data;
    },
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { email: string; password: string }) => {
      const res = await apiRequest<ApiResponse<TokenResponse>>("/auth/login", {
        method: "POST",
        body: JSON.stringify(vars),
      });
      return res.data;
    },
    onSuccess: (data) => {
      setTokens(data.access_token);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      name: string;
      email: string;
      password: string;
      role?: string;
      phone?: string;
    }) => {
      const res = await apiRequest<ApiResponse<{ user: UserResponse; tokens: TokenResponse }>>(
        "/auth/register",
        { method: "POST", body: JSON.stringify(vars) }
      );
      return res.data;
    },
    onSuccess: (data) => {
      setTokens(data.tokens.access_token);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiRequest("/auth/logout", { method: "POST" });
    },
    onSuccess: () => {
      clearTokens();
      qc.clear();
    },
  });
}
