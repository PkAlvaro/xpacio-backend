import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getAccessToken } from "@/lib/api";
import type { ApiResponse, AdminStats, AdminSpaceListItem, AdminSpaceCreate, AdminSpaceUpdate, SpaceDetail, AdminUserListItem, AdminReservationItem, SpaceImage, SystemConfig, HealthStatus } from "@/types/api";

// ── Stats ──────────────────────────────────────────────────────────────────
export function useAdminStats() {
  return useQuery({
    queryKey: ["admin", "stats"],
    queryFn: () => apiRequest<ApiResponse<AdminStats>>("/admin/stats").then(r => r.data),
    staleTime: 30_000,
  });
}

// ── Spaces list ────────────────────────────────────────────────────────────
export function useAdminSpaces(params: { q?: string; active_only?: boolean; page?: number; page_size?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.active_only !== undefined) qs.set("active_only", String(params.active_only));
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));

  return useQuery({
    queryKey: ["admin", "spaces", params],
    queryFn: () => apiRequest<ApiResponse<AdminSpaceListItem[]>>(`/admin/spaces?${qs}`).then(r => ({ items: r.data, meta: r.meta })),
    staleTime: 15_000,
  });
}

// ── Space detail ───────────────────────────────────────────────────────────
export function useAdminSpace(id: string | undefined) {
  return useQuery({
    queryKey: ["admin", "spaces", id],
    queryFn: () => apiRequest<ApiResponse<SpaceDetail>>(`/admin/spaces/${id}`).then(r => r.data),
    enabled: !!id,
  });
}

// ── Create space ───────────────────────────────────────────────────────────
export function useCreateAdminSpace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AdminSpaceCreate) =>
      apiRequest<ApiResponse<SpaceDetail>>("/admin/spaces", { method: "POST", body: JSON.stringify(data) }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "spaces"] }),
  });
}

// ── Update space ───────────────────────────────────────────────────────────
export function useUpdateAdminSpace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AdminSpaceUpdate }) =>
      apiRequest<ApiResponse<SpaceDetail>>(`/admin/spaces/${id}`, { method: "PATCH", body: JSON.stringify(data) }).then(r => r.data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ["admin", "spaces"] });
      qc.invalidateQueries({ queryKey: ["space", id] });
    },
  });
}

// ── Delete space ───────────────────────────────────────────────────────────
export function useDeleteAdminSpace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiRequest(`/admin/spaces/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "spaces"] }),
  });
}

// ── Images ─────────────────────────────────────────────────────────────────
export function useUploadImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, file, setPrimary }: { spaceId: string; file: File; setPrimary?: boolean }) => {
      const form = new FormData();
      form.append("file", file);
      const token = getAccessToken();
      return fetch(`${import.meta.env.VITE_API_URL ?? "/api/v1"}/admin/spaces/${spaceId}/images${setPrimary ? "?set_primary=true" : ""}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      }).then(r => r.json()).then(r => r.data as SpaceImage);
    },
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["admin", "spaces", spaceId] }),
  });
}

export function useDeleteImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, imageId }: { spaceId: string; imageId: string }) =>
      apiRequest(`/admin/spaces/${spaceId}/images/${imageId}`, { method: "DELETE" }),
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["admin", "spaces", spaceId] }),
  });
}

export function useSetPrimaryImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, imageId }: { spaceId: string; imageId: string }) =>
      apiRequest(`/admin/spaces/${spaceId}/images/${imageId}/primary`, { method: "PATCH" }),
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["admin", "spaces", spaceId] }),
  });
}

export function useReorderAdminImages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, order }: { spaceId: string; order: { id: string; display_order: number }[] }) =>
      apiRequest(`/admin/spaces/${spaceId}/images/order`, { method: "PATCH", body: JSON.stringify(order) }),
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["admin", "spaces", spaceId] }),
  });
}

// ── Schedules ──────────────────────────────────────────────────────────────
export function useSetAdminSchedules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, schedules }: { spaceId: string; schedules: Array<{ day_of_week: number; open_time: string; close_time: string }> }) =>
      apiRequest(`/admin/spaces/${spaceId}/schedules`, { method: "PUT", body: JSON.stringify(schedules) }).then(r => (r as any).data),
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["admin", "spaces", spaceId] }),
  });
}

// ── Users ──────────────────────────────────────────────────────────────────
export function useAdminUsers(params: { page?: number; page_size?: number; q?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  if (params.q) qs.set("q", params.q);
  return useQuery({
    queryKey: ["admin", "users", params],
    queryFn: () => apiRequest<ApiResponse<AdminUserListItem[]>>(`/admin/users?${qs}`).then(r => ({ items: r.data, meta: r.meta })),
    staleTime: 15_000,
  });
}

export function useChangeRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      apiRequest(`/admin/users/${userId}/role`, { method: "PATCH", body: JSON.stringify({ role }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
}

export function useToggleUserStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, is_active }: { userId: string; is_active: boolean }) =>
      apiRequest(`/admin/users/${userId}/status`, { method: "PATCH", body: JSON.stringify({ is_active }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
}

// ── Reservations ───────────────────────────────────────────────────────────
export function useAdminReservations(params: { status?: string; page?: number; page_size?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  return useQuery({
    queryKey: ["admin", "reservations", params],
    queryFn: () => apiRequest<ApiResponse<AdminReservationItem[]>>(`/admin/reservations?${qs}`).then(r => ({ items: r.data ?? [], meta: r.meta })),
    staleTime: 15_000,
  });
}

export function useAdminCancelReservation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reservationId, reason }: { reservationId: string; reason?: string }) =>
      apiRequest(`/admin/reservations/${reservationId}/cancel`, { method: "POST", body: JSON.stringify({ reason: reason ?? null }) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "reservations"] });
      qc.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });
}

export function useAdminHealth() {
  return useQuery({
    queryKey: ["admin", "health"],
    queryFn: () => apiRequest<ApiResponse<HealthStatus>>("/admin/health").then(r => r.data),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useSystemConfig() {
  return useQuery({
    queryKey: ["admin", "config"],
    queryFn: () => apiRequest<ApiResponse<SystemConfig>>("/admin/config").then(r => r.data),
    staleTime: 60_000,
  });
}

export function useUpdateSystemConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<SystemConfig>) =>
      apiRequest<ApiResponse<SystemConfig>>("/admin/config", { method: "PATCH", body: JSON.stringify(data) }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "config"] }),
  });
}
