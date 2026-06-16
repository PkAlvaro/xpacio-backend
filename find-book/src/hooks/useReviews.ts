import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { ApiResponse, Review, ReviewCreate } from "@/types/api";

export function useSpaceReviews(spaceId: string | undefined, page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ["space-reviews", spaceId, page, pageSize],
    queryFn: async () => {
      const res = await apiRequest<ApiResponse<Review[]>>(
        `/spaces/${spaceId}/reviews?page=${page}&page_size=${pageSize}`
      );
      return { items: res.data, meta: res.meta };
    },
    enabled: !!spaceId,
  });
}

export function useCreateReview(reservationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: ReviewCreate) => {
      const res = await apiRequest<ApiResponse<Review>>(
        `/reservations/${reservationId}/review`,
        { method: "POST", body: JSON.stringify(data) }
      );
      return res.data;
    },
    onSuccess: (_data, _vars) => {
      qc.invalidateQueries({ queryKey: ["space-reviews"] });
      qc.invalidateQueries({ queryKey: ["space"] });
    },
  });
}
