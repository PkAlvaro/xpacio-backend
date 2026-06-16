import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Lock, CreditCard, Globe } from "lucide-react";
import { fetchSpace, formatCLP } from "@/lib/spaces";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Steps } from "./Booking";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface PaymentState {
  spaceId: string;
  date: string;
  start: string;
  end: string;
  reservation: { id: string; total: number; subtotal: number };
}

type Provider = "transbank" | "stripe";

interface InitiateResponse {
  redirect_url: string;
  payment_id: string;
}

const Payment = () => {
  const { state } = useLocation() as { state: PaymentState | null };
  const [provider, setProvider] = useState<Provider>("transbank");
  const [loading, setLoading] = useState(false);

  const { data: space } = useQuery({
    queryKey: ["space", state?.spaceId],
    queryFn: () => fetchSpace(state!.spaceId),
    enabled: !!state?.spaceId,
  });

  if (!state?.reservation?.id) return <Navigate to="/buscar" replace />;
  const { reservation } = state;

  const pay = async () => {
    setLoading(true);
    try {
      const res = await api<InitiateResponse>(`/payments/${provider}/initiate`, {
        method: "POST",
        body: { reservation_id: reservation.id },
      });
      // Redirige a la pasarela (Webpay o Stripe Checkout)
      window.location.href = res.redirect_url;
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "No se pudo iniciar el pago";
      if (provider === "stripe") {
        toast.error("Stripe no está configurado en este entorno. Usa Transbank (Webpay).");
      } else {
        toast.error(msg);
      }
      setLoading(false);
    }
  };

  return (
    <div className="container max-w-3xl py-10">
      <Steps current={2} />
      <h1 className="font-display text-3xl font-bold mt-8 mb-6">Pago seguro</h1>

      <div className="grid md:grid-cols-[1fr_320px] gap-6">
        <div className="bg-card border border-border rounded-2xl p-6 shadow-soft space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Lock className="w-4 h-4" /> Pago procesado en ambiente de integración (sandbox)
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Elige tu método de pago</label>
            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => setProvider("transbank")}
                className={cn("p-4 rounded-xl border text-left transition-smooth", provider === "transbank" ? "border-primary ring-2 ring-primary/30" : "border-border hover:border-foreground")}>
                <CreditCard className="w-5 h-5 mb-2" />
                <p className="font-semibold text-sm">Transbank Webpay</p>
                <p className="text-xs text-muted-foreground">Tarjetas chilenas (débito/crédito)</p>
              </button>
              <button onClick={() => setProvider("stripe")}
                className={cn("p-4 rounded-xl border text-left transition-smooth", provider === "stripe" ? "border-primary ring-2 ring-primary/30" : "border-border hover:border-foreground")}>
                <Globe className="w-5 h-5 mb-2" />
                <p className="font-semibold text-sm">Stripe</p>
                <p className="text-xs text-muted-foreground">Tarjetas internacionales</p>
              </button>
            </div>
          </div>

          {provider === "transbank" ? (
            <div className="text-xs text-muted-foreground bg-secondary/50 rounded-xl p-3 space-y-1">
              <p className="font-medium text-foreground">Tarjeta de prueba (integración):</p>
              <p>VISA: 4051 8856 0044 6623 · CVV 123</p>
              <p>RUT: 11.111.111-1 · Clave: 123</p>
            </div>
          ) : (
            <div className="text-xs text-muted-foreground bg-secondary/50 rounded-xl p-3 space-y-1">
              <p className="font-medium text-foreground">Tarjeta de prueba Stripe:</p>
              <p>4242 4242 4242 4242 · CVV 123 · fecha futura</p>
              <p className="text-amber-600">Requiere STRIPE_SECRET_KEY configurada.</p>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-card border border-border rounded-2xl p-5 shadow-soft">
            <div className="flex gap-3 mb-4">
              {space && <img src={space.image} alt={space.name} className="w-16 h-16 rounded-lg object-cover" />}
              <div>
                <p className="font-semibold text-sm leading-tight">{space?.name}</p>
                <p className="text-xs text-muted-foreground mt-1">{state.date} · {state.start}–{state.end}</p>
              </div>
            </div>
            <div className="space-y-1.5 text-sm pt-3 border-t border-border">
              <div className="flex justify-between"><span className="text-muted-foreground">Subtotal</span><span>{formatCLP(reservation.subtotal)}</span></div>
              {reservation.total < reservation.subtotal && (
                <div className="flex justify-between text-primary"><span>Descuento</span><span>-{formatCLP(reservation.subtotal - reservation.total)}</span></div>
              )}
              <div className="flex justify-between"><span className="text-muted-foreground">Servicio</span><span>Gratis</span></div>
              <div className="flex justify-between font-bold pt-2 border-t border-border"><span>Total</span><span>{formatCLP(reservation.total)}</span></div>
            </div>
          </div>
          <Button onClick={pay} variant="hero" size="xl" className="w-full" disabled={loading}>
            {loading ? "Redirigiendo…" : `Pagar ${formatCLP(reservation.total)}`}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Payment;
