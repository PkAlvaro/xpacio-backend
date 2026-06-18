import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getAccessToken } from "@/lib/api";
import type { ApiResponse, SpaceDetail, SpaceImage } from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

export function useProviderSpace(id: string | undefined) {
  return useQuery({
    queryKey: ["provider-space", id],
    queryFn: () => apiRequest<ApiResponse<SpaceDetail>>(`/spaces/${id}`).then(r => r.data),
    enabled: !!id,
  });
}

export function useCreateProviderSpace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: object) =>
      apiRequest<ApiResponse<SpaceDetail>>("/spaces", { method: "POST", body: JSON.stringify(data) }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-spaces"] }),
  });
}

export function useUpdateProviderSpace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) =>
      apiRequest<ApiResponse<SpaceDetail>>(`/spaces/${id}`, { method: "PATCH", body: JSON.stringify(data) }).then(r => r.data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ["my-spaces"] });
      qc.invalidateQueries({ queryKey: ["provider-space", id] });
    },
  });
}

export function useProviderUploadImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, file }: { spaceId: string; file: File }) => {
      const form = new FormData();
      form.append("file", file);
      const token = getAccessToken();
      return fetch(`${BASE_URL}/spaces/${spaceId}/images`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
        credentials: "include",
      }).then(r => r.json()).then(r => r.data as SpaceImage);
    },
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["provider-space", spaceId] }),
  });
}

export function useProviderDeleteImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, imageId }: { spaceId: string; imageId: string }) =>
      apiRequest(`/spaces/${spaceId}/images/${imageId}`, { method: "DELETE" }),
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["provider-space", spaceId] }),
  });
}

export function useProviderSetPrimaryImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, imageId }: { spaceId: string; imageId: string }) =>
      apiRequest(`/spaces/${spaceId}/images/${imageId}/primary`, { method: "PATCH" }),
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["provider-space", spaceId] }),
  });
}

export function useProviderReorderImages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, order }: { spaceId: string; order: { id: string; display_order: number }[] }) =>
      apiRequest(`/spaces/${spaceId}/images/order`, { method: "PATCH", body: JSON.stringify(order) }),
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["provider-space", spaceId] }),
  });
}

export function useProviderSetSchedules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ spaceId, schedules }: { spaceId: string; schedules: Array<{ day_of_week: number; open_time: string; close_time: string }> }) =>
      apiRequest(`/spaces/${spaceId}/schedules`, { method: "PUT", body: JSON.stringify(schedules) }),
    onSuccess: (_, { spaceId }) => qc.invalidateQueries({ queryKey: ["provider-space", spaceId] }),
  });
}
