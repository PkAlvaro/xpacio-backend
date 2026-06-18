import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, Building2, Users, CalendarCheck, AlertTriangle, Settings, LogOut, ChevronRight, Menu, X } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useMe } from "@/hooks/useAuth";
import { clearTokens } from "@/lib/api";

const NAV = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/espacios", label: "Espacios", icon: Building2 },
  { to: "/admin/reservaciones", label: "Reservaciones", icon: CalendarCheck },
  { to: "/admin/reclamaciones", label: "Reclamaciones", icon: AlertTriangle },
  { to: "/admin/usuarios", label: "Usuarios", icon: Users },
  { to: "/admin/configuracion", label: "Configuración", icon: Settings },
];

export default function AdminLayout() {
  const { data: user, isLoading } = useMe();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  if (isLoading) return <div className="min-h-screen bg-background" />;

  if (!user || user.role !== "admin") {
    navigate("/login");
    return null;
  }

  const logout = () => { clearTokens(); navigate("/login"); };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Mobile overlay */}
      {open && (
        <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={() => setOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-64 bg-card border-r border-border flex flex-col transition-transform duration-300 lg:translate-x-0 lg:static lg:z-auto",
        open ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="h-16 flex items-center px-6 border-b border-border gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary grid place-items-center">
            <Building2 className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-display font-bold text-lg">Xpacio Admin</span>
          <button className="ml-auto lg:hidden" onClick={() => setOpen(false)}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setOpen(false)}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-smooth",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
              <ChevronRight className="w-3.5 h-3.5 ml-auto opacity-50" />
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3 px-3 py-2 mb-2">
            <div className="w-8 h-8 rounded-full bg-primary/10 grid place-items-center shrink-0">
              <span className="text-xs font-bold text-primary">{user.name[0]}</span>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{user.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-smooth"
          >
            <LogOut className="w-4 h-4" /> Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-border bg-card flex items-center px-6 gap-4 lg:hidden sticky top-0 z-30">
          <button onClick={() => setOpen(true)}>
            <Menu className="w-5 h-5" />
          </button>
          <span className="font-display font-bold">Admin</span>
        </header>
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
