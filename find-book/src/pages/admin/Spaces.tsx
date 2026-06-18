import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Search, Pencil, Trash2, ToggleLeft, ToggleRight, Star, CheckCircle, XCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAdminSpaces, useDeleteAdminSpace, useUpdateAdminSpace, useApproveSpace, useRejectSpace } from "@/hooks/useAdmin";
import type { AdminSpaceListItem, SpaceApprovalStatus } from "@/types/api";

const formatCLP = (n: number) => new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(n);

const PLACEHOLDER = "https://images.unsplash.com/photo-1497366216548-37526070297c?w=200&q=60";

export default function Spaces() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined);
  const [filterApproval, setFilterApproval] = useState<SpaceApprovalStatus | undefined>(undefined);

  const { data, isLoading } = useAdminSpaces({ q: q || undefined, active_only: filterActive, page, page_size: 15 });
  const deleteSpace = useDeleteAdminSpace();
  const updateSpace = useUpdateAdminSpace();
  const approveSpace = useApproveSpace();
  const rejectSpace = useRejectSpace();

  const allSpaces = data?.items ?? [];
  const spacesFiltered = filterApproval
    ? allSpaces.filter(s => (s.approval_status ?? "approved") === filterApproval)
    : allSpaces;

  const spaces = spacesFiltered;
  const total = data?.meta?.total ?? 0;
  const totalPages = Math.ceil(total / 15);

  const handleToggleActive = async (s: AdminSpaceListItem) => {
    await updateSpace.mutateAsync({ id: s.id, data: { is_active: !s.is_active } });
    toast.success(s.is_active ? "Espacio desactivado" : "Espacio activado");
  };

  const handleDelete = async (s: AdminSpaceListItem) => {
    if (!confirm(`¿Eliminar permanentemente "${s.name}"? Esta acción no se puede deshacer.`)) return;
    await deleteSpace.mutateAsync(s.id);
    toast.success("Espacio eliminado");
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-bold">Espacios</h1>
          <p className="text-muted-foreground mt-1">{total} espacios en total</p>
        </div>
        <Button variant="hero" onClick={() => navigate("/admin/espacios/nuevo")}>
          <Plus className="w-4 h-4" /> Nuevo espacio
        </Button>
      </div>

      {/* Filtros */}
      <div className="flex gap-3 mb-5 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={q}
            onChange={e => { setQ(e.target.value); setPage(1); }}
            placeholder="Buscar por nombre..."
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-border bg-card text-sm outline-none focus:ring-2 ring-primary/20"
          />
        </div>
        <div className="flex rounded-xl border border-border overflow-hidden text-sm">
          {([["Todos", undefined], ["Activos", true], ["Inactivos", false]] as const).map(([label, val]) => (
            <button key={label} onClick={() => { setFilterActive(val as any); setPage(1); }}
              className={cn("px-4 py-2 transition-smooth", filterActive === val ? "bg-foreground text-background" : "hover:bg-secondary")}>
              {label}
            </button>
          ))}
        </div>
        <div className="flex rounded-xl border border-border overflow-hidden text-sm">
          {([["Aprobación", undefined], ["Pendiente", "pending"], ["Aprobado", "approved"], ["Rechazado", "rejected"]] as const).map(([label, val]) => (
            <button key={label} onClick={() => setFilterApproval(val as SpaceApprovalStatus | undefined)}
              className={cn("px-4 py-2 transition-smooth", filterApproval === val ? "bg-foreground text-background" : "hover:bg-secondary")}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Cargando...</div>
        ) : spaces.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">No hay espacios con esos filtros.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-secondary/50">
              <tr>
                <th className="text-left py-3 px-4 font-semibold">Espacio</th>
                <th className="text-left py-3 px-4 font-semibold hidden md:table-cell">Ciudad</th>
                <th className="text-left py-3 px-4 font-semibold hidden lg:table-cell">Precio/hr</th>
                <th className="text-left py-3 px-4 font-semibold hidden lg:table-cell">Rating</th>
                <th className="text-left py-3 px-4 font-semibold">Estado</th>
                <th className="text-left py-3 px-4 font-semibold hidden xl:table-cell">Aprobación</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {spaces.map((s) => (
                <tr key={s.id} className="border-b border-border last:border-0 hover:bg-secondary/30 transition-smooth">
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl overflow-hidden bg-muted shrink-0">
                        <img src={s.primary_image ?? PLACEHOLDER} alt={s.name} className="w-full h-full object-cover" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium truncate max-w-xs">{s.name}</p>
                        <p className="text-xs text-muted-foreground">{s.type}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-muted-foreground hidden md:table-cell">{s.city}</td>
                  <td className="py-3 px-4 font-medium hidden lg:table-cell">{formatCLP(s.price_per_hour)}</td>
                  <td className="py-3 px-4 hidden lg:table-cell">
                    <span className="flex items-center gap-1">
                      <Star className="w-3.5 h-3.5 fill-foreground" /> {s.rating.toFixed(1)}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <button onClick={() => handleToggleActive(s)} title={s.is_active ? "Desactivar" : "Activar"}>
                      {s.is_active
                        ? <ToggleRight className="w-6 h-6 text-success" />
                        : <ToggleLeft className="w-6 h-6 text-muted-foreground" />}
                    </button>
                  </td>
                  <td className="py-3 px-4 hidden xl:table-cell">
                    <ApprovalBadge status={s.approval_status ?? "approved"} />
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-1 justify-end">
                      {(s.approval_status === "pending" || s.approval_status === "rejected") && (
                        <button
                          onClick={async () => { await approveSpace.mutateAsync(s.id); toast.success("Espacio aprobado"); }}
                          title="Aprobar"
                          className="p-2 rounded-lg hover:bg-green-100 text-muted-foreground hover:text-green-700 transition-smooth"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                      )}
                      {(s.approval_status === "pending" || s.approval_status === "approved") && (
                        <button
                          onClick={async () => {
                            const note = prompt("Motivo del rechazo (opcional):");
                            await rejectSpace.mutateAsync({ spaceId: s.id, note: note ?? undefined });
                            toast.success("Espacio rechazado");
                          }}
                          title="Rechazar"
                          className="p-2 rounded-lg hover:bg-red-100 text-muted-foreground hover:text-red-700 transition-smooth"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      )}
                      <Link to={`/admin/espacios/${s.id}/editar`}
                        className="p-2 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition-smooth">
                        <Pencil className="w-4 h-4" />
                      </Link>
                      <button onClick={() => handleDelete(s)}
                        className="p-2 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-smooth">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Paginación */}
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

function ApprovalBadge({ status }: { status: SpaceApprovalStatus }) {
  if (status === "approved") return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400">
      <CheckCircle className="w-3.5 h-3.5" /> Aprobado
    </span>
  );
  if (status === "pending") return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-yellow-700 dark:text-yellow-400">
      <Clock className="w-3.5 h-3.5" /> Pendiente
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-red-700 dark:text-red-400">
      <XCircle className="w-3.5 h-3.5" /> Rechazado
    </span>
  );
}
