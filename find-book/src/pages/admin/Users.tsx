import { useState } from "react";
import { Search, ShieldCheck, UserCheck, UserX, StickyNote, ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAdminUsers, useChangeRole, useToggleUserStatus, useUserNotes, useAddUserNote, useDeleteUserNote } from "@/hooks/useAdmin";
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
  const [expandedNotes, setExpandedNotes] = useState<string | null>(null);
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
                <>
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
                          onClick={() => setExpandedNotes(expandedNotes === u.id ? null : u.id)}
                          title="Notas internas"
                          className="p-2 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition-smooth"
                        >
                          {expandedNotes === u.id ? <ChevronUp className="w-4 h-4" /> : <StickyNote className="w-4 h-4" />}
                        </button>
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
                  {expandedNotes === u.id && (
                    <tr key={`notes-${u.id}`} className="border-b border-border bg-secondary/20">
                      <td colSpan={5} className="px-4 py-4">
                        <UserNotesPanel userId={u.id} />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Notas panel — rendered outside table to avoid layout issues */}

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

function UserNotesPanel({ userId }: { userId: string }) {
  const [newNote, setNewNote] = useState("");
  const { data: notes = [], isLoading } = useUserNotes(userId);
  const addNote = useAddUserNote();
  const deleteNote = useDeleteUserNote();

  const handleAdd = async () => {
    if (newNote.trim().length < 3) return;
    await addNote.mutateAsync({ userId, body: newNote.trim() });
    setNewNote("");
    toast.success("Nota guardada");
  };

  return (
    <div className="max-w-xl space-y-3">
      <p className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
        <StickyNote className="w-3.5 h-3.5" /> Notas internas
      </p>
      {isLoading ? (
        <p className="text-xs text-muted-foreground">Cargando…</p>
      ) : notes.length === 0 ? (
        <p className="text-xs text-muted-foreground">Sin notas.</p>
      ) : (
        <div className="space-y-2">
          {notes.map(n => (
            <div key={n.id} className="flex items-start gap-2 bg-card border border-border rounded-xl px-3 py-2">
              <p className="text-sm flex-1">{n.body}</p>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {new Date(n.created_at).toLocaleDateString("es-CL", { day: "2-digit", month: "short" })}
                </span>
                <button
                  onClick={() => deleteNote.mutateAsync({ userId, noteId: n.id })}
                  className="p-1 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-smooth"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <input
          value={newNote}
          onChange={e => setNewNote(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") handleAdd(); }}
          placeholder="Agregar nota interna…"
          className="flex-1 px-3 py-2 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20"
        />
        <Button size="sm" variant="hero" disabled={newNote.trim().length < 3 || addNote.isPending} onClick={handleAdd}>
          Guardar
        </Button>
      </div>
    </div>
  );
}
