import { useState } from "react";
import { Ban } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAdminReservations, useAdminCancelReservation } from "@/hooks/useAdmin";
import type { AdminReservationItem } from "@/types/api";

const formatCLP = (n: number) =>
  new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(n);

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  confirmed: "Confirmada",
  active: "Activa",
  finished: "Completada",
  cancelled: "Cancelada",
  expired: "Expirada",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  confirmed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  active: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  finished: "bg-secondary text-muted-foreground",
  cancelled: "bg-destructive/10 text-destructive",
  expired: "bg-muted text-muted-foreground",
};

const STATUS_FILTERS = [
  [undefined, "Todas"],
  ["pending", "Pendientes"],
  ["confirmed", "Confirmadas"],
  ["active", "Activas"],
  ["finished", "Completadas"],
  ["cancelled", "Canceladas"],
] as const;

const PAGE_SIZE = 30;

export default function Reservations() {
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useAdminReservations({ status, page, page_size: PAGE_SIZE });
  const cancelMut = useAdminCancelReservation();

  const reservations = data?.items ?? [];
  const total = data?.meta?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const handleCancel = async (r: AdminReservationItem) => {
    if (!confirm(`¿Cancelar reserva de ${r.client_name ?? "este cliente"} en "${r.space_name}"?`)) return;
    await cancelMut.mutateAsync({ reservationId: r.id });
    toast.success("Reserva cancelada");
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-display text-3xl font-bold">Reservaciones</h1>
        <p className="text-muted-foreground mt-1">{total} reservas en total</p>
      </div>

      {/* Filtros de estado */}
      <div className="flex gap-1.5 mb-5 flex-wrap">
        {STATUS_FILTERS.map(([val, label]) => (
          <button
            key={label}
            onClick={() => { setStatus(val); setPage(1); }}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs font-medium transition-smooth border",
              status === val
                ? "bg-foreground text-background border-foreground"
                : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Cargando...</div>
        ) : reservations.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            No hay reservas{status ? ` con estado "${STATUS_LABELS[status]}"` : ""}.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-secondary/50">
                <tr>
                  <th className="text-left py-3 px-4 font-semibold">Espacio</th>
                  <th className="text-left py-3 px-4 font-semibold hidden md:table-cell">Arrendatario</th>
                  <th className="text-left py-3 px-4 font-semibold hidden lg:table-cell">Fecha</th>
                  <th className="text-left py-3 px-4 font-semibold hidden lg:table-cell">Horario</th>
                  <th className="text-left py-3 px-4 font-semibold">Total</th>
                  <th className="text-left py-3 px-4 font-semibold">Estado</th>
                  <th className="py-3 px-4"></th>
                </tr>
              </thead>
              <tbody>
                {reservations.map(r => (
                  <tr key={r.id} className="border-b border-border last:border-0 hover:bg-secondary/30 transition-smooth">
                    <td className="py-3 px-4">
                      <p className="font-medium truncate max-w-[160px]">{r.space_name ?? "—"}</p>
                    </td>
                    <td className="py-3 px-4 hidden md:table-cell">
                      <p className="font-medium">{r.client_name ?? "—"}</p>
                      <p className="text-xs text-muted-foreground">{r.client_email}</p>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground hidden lg:table-cell">
                      {new Date(r.date).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "numeric" })}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground hidden lg:table-cell">
                      {r.start_time.slice(0, 5)}–{r.end_time.slice(0, 5)}
                      <span className="ml-1 text-xs">({r.hours}h)</span>
                    </td>
                    <td className="py-3 px-4 font-medium">{formatCLP(r.total)}</td>
                    <td className="py-3 px-4">
                      <span className={cn("text-xs font-medium px-2.5 py-1 rounded-full", STATUS_COLORS[r.status] ?? "bg-muted text-muted-foreground")}>
                        {STATUS_LABELS[r.status] ?? r.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {(r.status === "pending" || r.status === "confirmed") && (
                        <button
                          onClick={() => handleCancel(r)}
                          disabled={cancelMut.isPending}
                          title="Cancelar reserva"
                          className="p-2 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-smooth disabled:opacity-50"
                        >
                          <Ban className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-5">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Anterior</Button>
          <span className="text-sm text-muted-foreground">Página {page} de {totalPages}</span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Siguiente →</Button>
        </div>
      )}
    </div>
  );
}
