import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { ApiResponse, SpaceDetail, SpaceListItem, SpaceFilters, TimeSlot, SubSpaceItem } from "@/types/api";

export function useSpaces(filters: SpaceFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null) params.set(k, String(v));
  });

  return useQuery({
    queryKey: ["spaces", filters],
    queryFn: async () => {
      const res = await apiRequest<ApiResponse<SpaceListItem[]>>(`/spaces?${params}`);
      return { items: res.data, meta: res.meta };
    },
  });
}

export function useSpace(id: string | undefined) {
  return useQuery({
    queryKey: ["space", id],
    queryFn: async () => {
      const res = await apiRequest<ApiResponse<SpaceDetail>>(`/spaces/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useSubSpaces(spaceId: string | undefined) {
  return useQuery({
    queryKey: ["sub-spaces", spaceId],
    queryFn: async () => {
      const res = await apiRequest<ApiResponse<SubSpaceItem[]>>(`/spaces/${spaceId}/sub-spaces`);
      return res.data;
    },
    enabled: !!spaceId,
  });
}

export function useAvailability(
  spaceId: string | undefined,
  date: string | undefined,
  slotMinutes = 60
) {
  return useQuery({
    queryKey: ["availability", spaceId, date, slotMinutes],
    queryFn: async () => {
      const res = await apiRequest<ApiResponse<TimeSlot[]>>(
        `/spaces/${spaceId}/availability?date=${date}&slot_minutes=${slotMinutes}`
      );
      return res.data;
    },
    enabled: !!spaceId && !!date,
    staleTime: 30_000,
  });
}
