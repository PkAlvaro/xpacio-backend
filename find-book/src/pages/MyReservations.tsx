import { Link } from "react-router-dom";
import { Calendar, Clock, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useMyReservations, useCancelReservation } from "@/hooks/useReservations";
import { ApiError } from "@/lib/api";
import type { ReservationStatus } from "@/types/api";

const formatCLP = (n: number) =>
  new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" }).format(n);

const STATUS_LABEL: Record<ReservationStatus, string> = {
  pending: "Pendiente de pago",
  confirmed: "Confirmada",
  active: "En curso",
  finished: "Finalizada",
  cancelled: "Cancelada",
  expired: "Expirada",
};

const STATUS_CLASS: Record<ReservationStatus, string> = {
  pending: "bg-yellow-500/15 text-yellow-600",
  confirmed: "bg-blue-500/15 text-blue-600",
  active: "bg-success/15 text-success",
  finished: "bg-secondary text-muted-foreground",
  cancelled: "bg-destructive/15 text-destructive",
  expired: "bg-secondary text-muted-foreground",
};

interface ApiReservation {
  id: string;
  space_id: string;
  date: string;
  start_time: string;
  end_time: string;
  hours: number;
  total: number;
  status: "pending" | "confirmed" | "active" | "finished" | "cancelled" | "expired";
}

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente de pago",
  confirmed: "Confirmada",
  active: "En curso",
  finished: "Finalizada",
  cancelled: "Cancelada",
  expired: "Expirada",
};

const MyReservations = () => {
  const { data: reservations = [], isLoading } = useMyReservations();
  const cancel = useCancelReservation();

  const handleCancel = async (id: string) => {
    try {
      await cancel.mutateAsync({ id });
      toast.success("Reserva cancelada");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Error al cancelar");
    }
  };

  return (
    <div className="container py-10 max-w-4xl">
      <h1 className="font-display text-3xl md:text-4xl font-bold mb-2">Mis reservas</h1>
      <p className="text-muted-foreground mb-8">Gestiona tus arriendos pasados y próximos.</p>

      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-32 bg-muted rounded-2xl animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && reservations.length === 0 && (
        <div className="text-center py-20 border border-dashed border-border rounded-2xl">
          <p className="text-muted-foreground mb-4">Aún no tienes reservas.</p>
          <Link to="/buscar"><Button variant="hero">Explorar espacios</Button></Link>
        </div>
      )}

      {!isLoading && reservations.length > 0 && (
        <div className="space-y-4">
          {reservations.map((r) => (
            <div key={r.id} className="bg-card border border-border rounded-2xl p-4 shadow-soft flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <h3 className="font-semibold">Reserva #{r.id.slice(0, 8)}</h3>
                    <Link to={`/espacio/${r.space_id}`} className="text-sm text-primary hover:underline">
                      Ver espacio
                    </Link>
                  </div>
                  <span className={cn("px-3 py-1 rounded-full text-xs font-medium", STATUS_CLASS[r.status])}>
                    {STATUS_LABEL[r.status]}
                  </span>
                </div>
                <div className="flex flex-wrap gap-4 mt-3 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    {new Date(r.date).toLocaleDateString("es-CL")}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {r.start_time.slice(0, 5)} – {r.end_time.slice(0, 5)}
                  </span>
                  <span className="font-semibold text-foreground">{formatCLP(r.total)}</span>
                </div>
                <div className="flex gap-2 mt-4">
                  {(r.status === "pending" || r.status === "confirmed") && (
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={cancel.isPending}
                      onClick={() => handleCancel(r.id)}
                    >
                      <X className="w-4 h-4" /> Cancelar
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyReservations;
