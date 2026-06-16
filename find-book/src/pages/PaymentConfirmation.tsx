import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { apiRequest } from "@/lib/api";
import type { ApiResponse, Payment } from "@/types/api";

export default function PaymentConfirmation() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const token = params.get("token_ws");
    if (!token) {
      setStatus("error");
      setError("Token de pago no encontrado");
      return;
    }

    apiRequest<ApiResponse<Payment>>(`/payments/confirm?token_ws=${token}`, { method: "POST" })
      .then((res) => {
        if (res.data.status === "paid") {
          setStatus("success");
          setTimeout(() => navigate("/mis-reservas"), 3000);
        } else {
          setStatus("error");
          setError("El pago no fue autorizado");
        }
      })
      .catch((err) => {
        setStatus("error");
        setError(err.message ?? "Error al confirmar el pago");
      });
  }, [params, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="text-center max-w-sm">
        {status === "loading" && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
            <p className="text-muted-foreground">Confirmando pago...</p>
          </>
        )}
        {status === "success" && (
          <>
            <div className="text-5xl mb-4">✓</div>
            <h2 className="text-2xl font-bold mb-2">¡Pago confirmado!</h2>
            <p className="text-muted-foreground">Tu reserva fue confirmada. Redirigiendo...</p>
          </>
        )}
        {status === "error" && (
          <>
            <div className="text-5xl mb-4">✗</div>
            <h2 className="text-2xl font-bold mb-2">Error en el pago</h2>
            <p className="text-muted-foreground mb-4">{error}</p>
            <button
              className="text-primary underline"
              onClick={() => navigate("/")}
            >
              Volver al inicio
            </button>
          </>
        )}
      </div>
    </div>
  );
}
