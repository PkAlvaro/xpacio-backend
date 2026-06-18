import { useState } from "react";
import { Search, ShieldCheck, UserCheck, UserX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAdminUsers, useChangeRole, useToggleUserStatus } from "@/hooks/useAdmin";
import { useDebounce } from "@/hooks/useDebounce";
import type { AdminUserListItem } from "@/types/api";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  provider: "Anfitrión",
  client: "Cliente",
};

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-primary/10 text-primary",
  provider: "bg-blue-500/10 text-blue-600",
  client: "bg-secondary text-muted-foreground",
};

const ROLES_CYCLE: string[] = ["client", "provider", "admin"];

export default function Users() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const debouncedQ = useDebounce(q, 350);

  const { data, isLoading } = useAdminUsers({ page, page_size: 20, q: debouncedQ || undefined });
  const changeRole = useChangeRole();
  const toggleStatus = useToggleUserStatus();

  const users = data?.items ?? [];
  const total = data?.meta?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  const handleRoleChange = async (u: AdminUserListItem, newRole: string) => {
    await changeRole.mutateAsync({ userId: u.id, role: newRole });
    toast.success(`Rol cambiado a ${ROLE_LABELS[newRole]}`);
  };

  const handleStatusToggle = async (u: AdminUserListItem) => {
    await toggleStatus.mutateAsync({ userId: u.id, is_active: !u.is_active });
    toast.success(u.is_active ? "Usuario desactivado" : "Usuario activado");
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-bold">Usuarios</h1>
          <p className="text-muted-foreground mt-1">{total} usuarios registrados</p>
        </div>
      </div>

      <div className="relative mb-5 max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          value={q}
          onChange={e => { setQ(e.target.value); setPage(1); }}
          placeholder="Buscar por nombre o email..."
          className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-border bg-card text-sm outline-none focus:ring-2 ring-primary/20"
        />
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Cargando...</div>
        ) : users.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">No hay usuarios.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-secondary/50">
              <tr>
                <th className="text-left py-3 px-4 font-semibold">Usuario</th>
                <th className="text-left py-3 px-4 font-semibold hidden md:table-cell">Email</th>
                <th className="text-left py-3 px-4 font-semibold">Rol</th>
                <th className="text-left py-3 px-4 font-semibold">Estado</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-b border-border last:border-0 hover:bg-secondary/30 transition-smooth">
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary/10 grid place-items-center shrink-0">
                        <span className="text-xs font-bold text-primary">{u.name[0].toUpperCase()}</span>
                      </div>
                      <p className="font-medium">{u.name}</p>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-muted-foreground hidden md:table-cell">{u.email}</td>
                  <td className="py-3 px-4">
                    <select
                      value={u.role}
                      onChange={e => handleRoleChange(u, e.target.value)}
                      disabled={changeRole.isPending}
                      className={cn(
                        "text-xs font-medium px-2.5 py-1 rounded-full border-0 cursor-pointer outline-none",
                        ROLE_COLORS[u.role] ?? "bg-secondary text-muted-foreground"
                      )}
                    >
                      {ROLES_CYCLE.map(r => (
                        <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-3 px-4">
                    <span className={cn(
                      "inline-flex text-xs font-medium px-2.5 py-1 rounded-full",
                      u.is_active ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"
                    )}>
                      {u.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-1 justify-end">
                      {u.role === "admin" && (
                        <ShieldCheck className="w-4 h-4 text-primary mr-1" title="Administrador" />
                      )}
                      <button
                        onClick={() => handleStatusToggle(u)}
                        title={u.is_active ? "Desactivar" : "Activar"}
                        disabled={toggleStatus.isPending}
                        className={cn(
                          "p-2 rounded-lg transition-smooth disabled:opacity-50",
                          u.is_active
                            ? "hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                            : "hover:bg-success/10 text-muted-foreground hover:text-success"
                        )}
                      >
                        {u.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
