import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getAccessToken } from "@/lib/api";
import type { ApiResponse, DisputeItem } from "@/types/api";

export function useMyDisputes() {
  return useQuery({
    queryKey: ["disputes", "my"],
    queryFn: () => apiRequest<ApiResponse<DisputeItem[]>>("/disputes/my").then(r => r.data ?? []),
    staleTime: 30_000,
  });
}

export function useOpenDispute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reservationId, reason, files }: { reservationId: string; reason: string; files: File[] }) => {
      const form = new FormData();
      form.append("reason", reason);
      files.forEach(f => form.append("files", f));
      const token = getAccessToken();
      return fetch(
        `${import.meta.env.VITE_API_URL ?? "/api/v1"}/reservations/${reservationId}/dispute`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: form,
        }
      ).then(async r => {
        const json = await r.json();
        if (!r.ok) throw new Error(json?.detail ?? "Error al enviar reclamación");
        return json;
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["disputes", "my"] });
      qc.invalidateQueries({ queryKey: ["my-reservations"] });
    },
  });
}

export function useAdminDisputes(params: { status?: string; page?: number; page_size?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  return useQuery({
    queryKey: ["admin", "disputes", params],
    queryFn: () => apiRequest<ApiResponse<DisputeItem[]>>(`/admin/disputes?${qs}`).then(r => ({ items: r.data ?? [], meta: r.meta })),
    staleTime: 15_000,
  });
}

export function useResolveDispute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      disputeId,
      decision,
      adminNotes,
      refundAmount,
    }: {
      disputeId: string;
      decision: "refund" | "reject";
      adminNotes?: string;
      refundAmount?: number;
    }) =>
      apiRequest(`/admin/disputes/${disputeId}/resolve`, {
        method: "PATCH",
        body: JSON.stringify({ decision, admin_notes: adminNotes ?? null, refund_amount: refundAmount ?? null }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "disputes"] }),
  });
}
