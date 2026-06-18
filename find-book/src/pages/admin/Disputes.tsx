import { useState } from "react";
import { CheckCircle, XCircle, ChevronDown, ChevronUp, ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAdminDisputes, useResolveDispute } from "@/hooks/useDisputes";
import type { DisputeItem } from "@/types/api";

const formatCLP = (n: number) =>
  new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(n);

const STATUS_LABELS: Record<string, string> = {
  open: "Abierta",
  under_review: "En revisión",
  resolved_refund: "Reembolso aprobado",
  resolved_rejected: "Rechazada",
};

const STATUS_COLORS: Record<string, string> = {
  open: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  under_review: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  resolved_refund: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  resolved_rejected: "bg-secondary text-muted-foreground",
};

const STATUS_FILTERS = [
  [undefined, "Todas"],
  ["open", "Abiertas"],
  ["under_review", "En revisión"],
  ["resolved_refund", "Reembolso aprobado"],
  ["resolved_rejected", "Rechazadas"],
] as const;

function ResolveModal({
  dispute,
  onClose,
}: {
  dispute: DisputeItem;
  onClose: () => void;
}) {
  const [decision, setDecision] = useState<"refund" | "reject">("refund");
  const [notes, setNotes] = useState("");
  const [amount, setAmount] = useState<number>(dispute.refund_amount ?? 0);
  const mut = useResolveDispute();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await mut.mutateAsync({
      disputeId: dispute.id,
      decision,
      adminNotes: notes.trim() || undefined,
      refundAmount: decision === "refund" ? amount : undefined,
    });
    toast.success(decision === "refund" ? "Reembolso aprobado" : "Disputa rechazada");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-md">
        <div className="p-5 border-b border-border">
          <h2 className="font-semibold text-lg">Resolver reclamación</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {dispute.opener_name} — {dispute.space_name}
          </p>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Decisión</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setDecision("refund")}
                className={cn(
                  "flex-1 py-2.5 rounded-xl border text-sm font-medium transition-smooth",
                  decision === "refund"
                    ? "bg-success text-white border-success"
                    : "border-border text-muted-foreground hover:border-success/50"
                )}
              >
                <CheckCircle className="w-4 h-4 inline mr-1.5" />Aprobar reembolso
              </button>
              <button
                type="button"
                onClick={() => setDecision("reject")}
                className={cn(
                  "flex-1 py-2.5 rounded-xl border text-sm font-medium transition-smooth",
                  decision === "reject"
                    ? "bg-destructive text-white border-destructive"
                    : "border-border text-muted-foreground hover:border-destructive/50"
                )}
              >
                <XCircle className="w-4 h-4 inline mr-1.5" />Rechazar
              </button>
            </div>
          </div>

          {decision === "refund" && (
            <div>
              <label className="block text-sm font-medium mb-1.5">Monto a reembolsar (CLP)</label>
              <input
                type="number"
                min={0}
                value={amount}
                onChange={e => setAmount(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20"
              />
              <p className="text-xs text-muted-foreground mt-1">Total pagado por el cliente desconocido — consulta la reserva</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1.5">Notas internas (opcional)</label>
            <textarea
              rows={3}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Motivo de la decisión..."
              className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm resize-none outline-none focus:ring-2 ring-primary/20"
            />
          </div>

          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onClose}>Cancelar</Button>
            <Button
              type="submit"
              variant={decision === "refund" ? "hero" : "destructive"}
              disabled={mut.isPending}
            >
              {mut.isPending ? "Guardando…" : decision === "refund" ? "Aprobar reembolso" : "Rechazar disputa"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DisputeRow({ dispute }: { dispute: DisputeItem }) {
  const [expanded, setExpanded] = useState(false);
  const [resolving, setResolving] = useState(false);
  const isResolved = dispute.status === "resolved_refund" || dispute.status === "resolved_rejected";

  return (
    <>
      <tr className="border-b border-border last:border-0 hover:bg-secondary/20 transition-smooth">
        <td className="py-3 px-4">
          <p className="font-medium">{dispute.opener_name ?? "—"}</p>
          <p className="text-xs text-muted-foreground">{dispute.opener_email}</p>
        </td>
        <td className="py-3 px-4 hidden md:table-cell">
          <p className="truncate max-w-[140px]">{dispute.space_name ?? "—"}</p>
        </td>
        <td className="py-3 px-4 hidden lg:table-cell text-muted-foreground text-sm">
          {new Date(dispute.created_at).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "numeric" })}
        </td>
        <td className="py-3 px-4">
          <span className={cn("text-xs font-medium px-2.5 py-1 rounded-full", STATUS_COLORS[dispute.status] ?? "bg-muted")}>
            {STATUS_LABELS[dispute.status] ?? dispute.status}
          </span>
        </td>
        <td className="py-3 px-4 hidden lg:table-cell text-sm font-medium">
          {dispute.refund_amount != null ? formatCLP(dispute.refund_amount) : "—"}
        </td>
        <td className="py-3 px-4">
          <div className="flex items-center gap-1 justify-end">
            <button
              onClick={() => setExpanded(v => !v)}
              className="p-2 rounded-lg hover:bg-secondary text-muted-foreground transition-smooth"
              title="Ver detalle"
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {!isResolved && (
              <button
                onClick={() => setResolving(true)}
                className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-smooth"
              >
                Resolver
              </button>
            )}
          </div>
        </td>
      </tr>

      {expanded && (
        <tr className="bg-secondary/30">
          <td colSpan={6} className="px-4 py-4">
            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-1">MOTIVO</p>
                <p className="text-sm">{dispute.reason}</p>
              </div>
              {dispute.admin_notes && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-1">NOTAS ADMIN</p>
                  <p className="text-sm">{dispute.admin_notes}</p>
                </div>
              )}
              {dispute.evidence.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">EVIDENCIAS ({dispute.evidence.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {dispute.evidence.map(e => (
                      <a
                        key={e.id}
                        href={e.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs bg-card border border-border px-2.5 py-1.5 rounded-lg hover:bg-secondary transition-smooth"
                      >
                        <ImageIcon className="w-3.5 h-3.5" />
                        {e.filename ?? "imagen"}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}

      {resolving && (
        <ResolveModal dispute={dispute} onClose={() => setResolving(false)} />
      )}
    </>
  );
}

const PAGE_SIZE = 30;

export default function Disputes() {
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const { data, isLoading } = useAdminDisputes({ status, page, page_size: PAGE_SIZE });

  const disputes = data?.items ?? [];
  const total = data?.meta?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-display text-3xl font-bold">Reclamaciones</h1>
        <p className="text-muted-foreground mt-1">{total} reclamaciones en total</p>
      </div>

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
        ) : disputes.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">No hay reclamaciones.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-secondary/50">
                <tr>
                  <th className="text-left py-3 px-4 font-semibold">Cliente</th>
                  <th className="text-left py-3 px-4 font-semibold hidden md:table-cell">Espacio</th>
                  <th className="text-left py-3 px-4 font-semibold hidden lg:table-cell">Fecha</th>
                  <th className="text-left py-3 px-4 font-semibold">Estado</th>
                  <th className="text-left py-3 px-4 font-semibold hidden lg:table-cell">Reembolso</th>
                  <th className="py-3 px-4"></th>
                </tr>
              </thead>
              <tbody>
                {disputes.map(d => <DisputeRow key={d.id} dispute={d} />)}
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
