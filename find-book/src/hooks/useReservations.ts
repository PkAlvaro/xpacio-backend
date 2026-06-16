import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { ApiResponse, Reservation, PaymentInitiateResponse } from "@/types/api";

export function useMyReservations(status?: string) {
  const params = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["reservations", status],
    queryFn: async () => {
      const res = await apiRequest<ApiResponse<Reservation[]>>(`/reservations${params}`);
      return res.data;
    },
  });
}

export function useCreateReservation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      space_id: string;
      date: string;
      start_time: string;
      end_time: string;
    }) => {
      const res = await apiRequest<ApiResponse<Reservation>>("/reservations", {
        method: "POST",
        body: JSON.stringify(vars),
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reservations"] });
      qc.invalidateQueries({ queryKey: ["availability"] });
    },
  });
}

export function useCancelReservation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: string; reason?: string }) => {
      const res = await apiRequest<ApiResponse<Reservation>>(
        `/reservations/${vars.id}/cancel`,
        { method: "POST", body: JSON.stringify({ reason: vars.reason }) }
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reservations"] });
    },
  });
}

export function useInitiatePayment() {
  return useMutation({
    mutationFn: async (reservationId: string) => {
      const res = await apiRequest<ApiResponse<PaymentInitiateResponse>>(
        "/payments/initiate",
        { method: "POST", body: JSON.stringify({ reservation_id: reservationId }) }
      );
      return res.data;
    },
    onSuccess: (data) => {
      // redirect to Transbank
      window.location.href = data.webpay_url;
    },
  });
}
