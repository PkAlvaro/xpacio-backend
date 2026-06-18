import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, X, Loader2 } from "lucide-react";
import { apiRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";

type Status = "loading" | "success" | "failed";

const Shell = ({ status, title, message }: { status: Status; title: string; message: string }) => {
  const navigate = useNavigate();
  return (
    <div className="container max-w-xl py-20 text-center">
      {status === "loading" ? (
        <div className="w-20 h-20 rounded-full bg-secondary grid place-items-center mx-auto mb-6">
          <Loader2 className="w-10 h-10 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring" }}
          className={`w-20 h-20 rounded-full grid place-items-center mx-auto mb-6 ${status === "success" ? "bg-success" : "bg-destructive"}`}>
          {status === "success" ? <Check className="w-10 h-10 text-success-foreground" /> : <X className="w-10 h-10 text-destructive-foreground" />}
        </motion.div>
      )}
      <h1 className="font-display text-3xl font-bold mb-3">{title}</h1>
      <p className="text-muted-foreground mb-8">{message}</p>
      {status !== "loading" && (
        <div className="flex gap-3 justify-center">
          <Button variant="outline" onClick={() => navigate("/")}>Volver al inicio</Button>
          <Button variant="hero" onClick={() => navigate("/mis-reservas")}>Ver mis reservas</Button>
        </div>
      )}
    </div>
  );
};

// Transbank: vuelve a TRANSBANK_RETURN_URL?token_ws=... → confirmamos en el backend.
export const PaymentReturn = () => {
  const [params] = useSearchParams();
  const [status, setStatus] = useState<Status>("loading");

  const tokenWs = params.get("token_ws");
  const tbkToken = params.get("TBK_TOKEN"); // presente si el usuario aborta

  useEffect(() => {
    let cancelled = false;
    async function confirm() {
      if (!tokenWs) {
        // Pago anulado/abortado por el usuario
        if (!cancelled) setStatus("failed");
        return;
      }
      try {
        const json = await apiRequest("/payments/transbank/confirm", {
          method: "POST",
          query: { token_ws: tokenWs },
          auth: false,
        });
        const data = json?.data ?? json;
        if (!cancelled) setStatus(data?.status === "paid" ? "success" : "failed");
      } catch {
        if (!cancelled) setStatus("failed");
      }
    }
    confirm();
    return () => { cancelled = true; };
  }, [tokenWs, tbkToken]);

  if (status === "loading") return <Shell status="loading" title="Confirmando pago…" message="Estamos validando tu transacción con Transbank." />;
  if (status === "success") return <Shell status="success" title="¡Reserva confirmada!" message="Tu pago fue aprobado y la reserva quedó confirmada." />;
  return <Shell status="failed" title="Pago no completado" message="La transacción no se completó. El horario no quedó bloqueado; puedes intentarlo de nuevo." />;
};

// Stripe: success se confirma vía webhook; aquí solo mostramos el resultado.
export const PaymentSuccess = () => (
  <Shell status="success" title="¡Pago recibido!" message="Tu pago con Stripe fue procesado. La reserva se confirma automáticamente." />
);

export const PaymentCancelled = () => (
  <Shell status="failed" title="Pago cancelado" message="Cancelaste el pago. El horario no quedó bloqueado; puedes intentarlo nuevamente." />
);
