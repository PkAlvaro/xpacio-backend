import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Calendar, Clock, MapPin, Users } from "lucide-react";
import { fetchSpace, formatCLP } from "@/lib/spaces";
import { apiRequest, getAccessToken, ApiError } from "@/lib/api";
import type { ApiResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface BookingState {
  spaceId: string;
  date: string;
  start: string;
  end: string;
  hours: number;
  numPeople: number;
}

interface ReservationResponse {
  id: string;
  hours: number;
  num_people: number;
  subtotal: number;
  service_fee: number;
  total: number;
}

const Booking = () => {
  const navigate = useNavigate();
  const { state } = useLocation() as { state: BookingState | null };
  const [loading, setLoading] = useState(false);

  const { data: space } = useQuery({
    queryKey: ["space", state?.spaceId],
    queryFn: () => fetchSpace(state!.spaceId),
    enabled: !!state?.spaceId,
  });

  if (!state?.spaceId) return <Navigate to="/buscar" replace />;

  const effectivePerHour = (() => {
    if (!space) return 0;
    if (!space.discountActive || space.discountedPrice == null || space.discountedPrice >= space.price) return space.price;
    if (space.discountType === "volume") {
      const minPeople = space.discountMinPeople ?? 1;
      if ((state.numPeople || 1) < minPeople) return space.price;
    }
    return space.discountedPrice;
  })();
  const estTotal = effectivePerHour * state.hours;

  const confirm = async () => {
    if (!getAccessToken()) {
      toast.error("Inicia sesión para reservar");
      return navigate("/login");
    }
    setLoading(true);
    try {
      const res = await apiRequest<ApiResponse<ReservationResponse>>("/reservations", {
        method: "POST",
        body: JSON.stringify({
          space_id: state.spaceId,
          date: state.date,
          start_time: state.start,
          end_time: state.end,
          num_people: state.numPeople || 1,
        }),
      });
      const reservation = res.data!;
      navigate("/pago", { state: { ...state, reservation } });
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "No se pudo crear la reserva";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container max-w-3xl py-10">
      <Link to={`/espacio/${state.spaceId}`} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="w-4 h-4" /> Volver
      </Link>

      <Steps current={1} />

      <h1 className="font-display text-3xl font-bold mt-8 mb-6">Confirma tu reserva</h1>

      <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-soft">
        <div className="flex gap-4 p-4 border-b border-border">
          {space && <img src={space.image} alt={space.name} className="w-28 h-28 object-cover rounded-xl" />}
          <div>
            <h2 className="font-semibold">{space?.name || "…"}</h2>
            <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
              <MapPin className="w-3.5 h-3.5" /> {space?.location}
            </p>
            {space && <span className="inline-block mt-2 px-2 py-0.5 rounded-full bg-secondary text-xs">{space.type}</span>}
          </div>
        </div>

        <div className="p-5 space-y-3">
          <Row icon={<Calendar className="w-4 h-4" />} label="Fecha" value={new Date(state.date + "T00:00:00").toLocaleDateString("es-CL", { weekday: "long", day: "numeric", month: "long" })} />
          <Row icon={<Clock className="w-4 h-4" />} label="Horario" value={`${state.start} – ${state.end} (${state.hours}h)`} />
          <Row icon={<Users className="w-4 h-4" />} label="Personas" value={`${state.numPeople || 1}`} />
        </div>

        <div className="p-5 bg-secondary/40 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Estimado ({state.hours}h)</span>
            <span>{formatCLP(estTotal)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Cargo de servicio</span>
            <span>Gratis</span>
          </div>
          <div className="flex justify-between font-bold text-lg pt-2 border-t border-border">
            <span>Total estimado</span><span>{formatCLP(estTotal)}</span>
          </div>
          <p className="text-xs text-muted-foreground">El total final lo calcula el servidor al confirmar.</p>
        </div>
      </div>

      <Button variant="hero" size="xl" className="w-full mt-6" disabled={loading} onClick={confirm}>
        {loading ? "Creando reserva…" : "Continuar al pago"}
      </Button>
      <p className="text-xs text-muted-foreground text-center mt-3">No se realizará ningún cargo hasta confirmar el pago.</p>
    </div>
  );
};

const Row = ({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) => (
  <div className="flex items-start gap-3">
    <div className="w-8 h-8 rounded-lg bg-secondary grid place-items-center text-muted-foreground">{icon}</div>
    <div>
      <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
      <p className="font-medium capitalize">{value}</p>
    </div>
  </div>
);

export const Steps = ({ current }: { current: number }) => {
  const steps = ["Detalles", "Confirmar", "Pago", "Listo"];
  return (
    <div className="flex items-center gap-2">
      {steps.map((s, i) => (
        <div key={s} className="flex items-center gap-2 flex-1">
          <div className={`w-7 h-7 rounded-full grid place-items-center text-xs font-semibold transition-smooth ${
            i <= current ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground"
          }`}>{i + 1}</div>
          <span className={`text-xs hidden sm:inline ${i === current ? "font-semibold" : "text-muted-foreground"}`}>{s}</span>
          {i < steps.length - 1 && <div className={`flex-1 h-0.5 ${i < current ? "bg-primary" : "bg-border"}`} />}
        </div>
      ))}
    </div>
  );
};

export default Booking;
