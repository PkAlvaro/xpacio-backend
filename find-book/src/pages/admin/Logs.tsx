import { useState } from "react";
import { Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuditLogs } from "@/hooks/useAdmin";
import type { AuditLog } from "@/types/api";

const ACTION_LABELS: Record<string, string> = {
  user_role_changed: "Cambio de rol",
  user_status_toggled: "Toggle estado",
  user_note_added: "Nota agregada",
  space_approved: "Espacio aprobado",
  space_rejected: "Espacio rechazado",
};

const ACTION_COLORS: Record<string, string> = {
  user_role_changed: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  user_status_toggled: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  user_note_added: "bg-secondary text-muted-foreground",
  space_approved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  space_rejected: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

function LogRow({ log }: { log: AuditLog }) {
  const label = ACTION_LABELS[log.action] ?? log.action;
  const color = ACTION_COLORS[log.action] ?? "bg-secondary text-muted-foreground";

  return (
    <tr className="border-b border-border last:border-0 hover:bg-secondary/30 transition-smooth">
      <td className="py-3 px-4">
        <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${color}`}>{label}</span>
      </td>
      <td className="py-3 px-4 text-sm text-muted-foreground">{log.admin_name ?? log.admin_id ?? "—"}</td>
      <td className="py-3 px-4 text-sm text-muted-foreground">
        {log.target_type && <span className="font-mono text-xs">{log.target_type}</span>}
        {log.target_id && <span className="font-mono text-xs text-muted-foreground ml-1 opacity-60">{log.target_id.slice(0, 8)}…</span>}
      </td>
      <td className="py-3 px-4 text-sm text-muted-foreground max-w-xs truncate">
        {log.detail ? JSON.stringify(log.detail) : "—"}
      </td>
      <td className="py-3 px-4 text-xs text-muted-foreground whitespace-nowrap">
        {new Date(log.created_at).toLocaleString("es-CL", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
      </td>
    </tr>
  );
}

export default function Logs() {
  const [page, setPage] = useState(1);
  const [filterAction, setFilterAction] = useState<string | undefined>(undefined);

  const { data, isLoading } = useAuditLogs({ action: filterAction, page, page_size: 50 });
  const logs = data?.items ?? [];
  const total = data?.meta?.total ?? 0;
  const totalPages = Math.ceil(total / 50);

  const actions = Object.keys(ACTION_LABELS);

  return (
    <div>
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-bold flex items-center gap-3">
            <Activity className="w-7 h-7 text-muted-foreground" /> Registro de actividad
          </h1>
          <p className="text-muted-foreground mt-1">{total} eventos registrados</p>
        </div>
      </div>

      <div className="flex gap-1 mb-5 flex-wrap">
        <button
          onClick={() => { setFilterAction(undefined); setPage(1); }}
          className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-smooth border ${
            !filterAction ? "bg-foreground text-background border-foreground" : "border-border text-muted-foreground hover:text-foreground"
          }`}
        >
          Todos
        </button>
        {actions.map(a => (
          <button
            key={a}
            onClick={() => { setFilterAction(a); setPage(1); }}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-smooth border ${
              filterAction === a ? "bg-foreground text-background border-foreground" : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {ACTION_LABELS[a]}
          </button>
        ))}
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Cargando...</div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">Sin registros de actividad.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-secondary/50">
                <tr>
                  <th className="text-left py-3 px-4 font-semibold">Acción</th>
                  <th className="text-left py-3 px-4 font-semibold">Admin</th>
                  <th className="text-left py-3 px-4 font-semibold">Objetivo</th>
                  <th className="text-left py-3 px-4 font-semibold">Detalle</th>
                  <th className="text-left py-3 px-4 font-semibold">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => <LogRow key={log.id} log={log} />)}
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
