import { Link, NavLink, useNavigate } from "react-router-dom";
import { Building2, Menu, User, LayoutDashboard, LogOut, HomeIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useMe } from "@/hooks/useAuth";
import { clearTokens } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";

const links = [
  { to: "/", label: "Inicio" },
  { to: "/buscar", label: "Buscar espacios" },
  { to: "/mis-reservas", label: "Mis reservas" },
];

export const Navbar = () => {
  const [open, setOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: user, isLoading } = useMe();

  const logout = () => {
    clearTokens();
    qc.clear();
    navigate("/");
    setOpen(false);
    setUserMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-background/80 border-b border-border">
      <div className="container flex items-center justify-between h-16">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl gradient-hero grid place-items-center shadow-glow">
            <Building2 className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-display text-xl font-bold">Xpacio</span>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) =>
                cn(
                  "px-4 py-2 rounded-full text-sm font-medium transition-smooth",
                  isActive ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-2">
          {!isLoading && user ? (
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(v => !v)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-border hover:bg-secondary transition-smooth text-sm font-medium"
              >
                <div className="w-6 h-6 rounded-full bg-primary/10 grid place-items-center shrink-0">
                  <span className="text-xs font-bold text-primary">{user.name[0].toUpperCase()}</span>
                </div>
                {user.name.split(" ")[0]}
              </button>
              {userMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-48 bg-card border border-border rounded-xl shadow-lg py-1 z-50">
                  {user.role === "provider" && (
                    <Link
                      to="/mis-espacios"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-secondary transition-smooth"
                    >
                      <HomeIcon className="w-4 h-4" /> Mis espacios
                    </Link>
                  )}
                  {user.role === "admin" && (
                    <Link
                      to="/admin"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-secondary transition-smooth"
                    >
                      <LayoutDashboard className="w-4 h-4" /> Panel Admin
                    </Link>
                  )}
                  <button
                    onClick={logout}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-destructive hover:bg-destructive/10 transition-smooth"
                  >
                    <LogOut className="w-4 h-4" /> Cerrar sesión
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Button variant="ghost" onClick={() => navigate("/login")}>Iniciar sesión</Button>
              <Button variant="hero" onClick={() => navigate("/registro")}>Registrarse</Button>
            </>
          )}
        </div>

        <button className="md:hidden p-2" onClick={() => setOpen(!open)} aria-label="Menu">
          <Menu className="w-6 h-6" />
        </button>
      </div>

      {open && (
        <div className="md:hidden border-t border-border bg-background">
          <div className="container py-3 flex flex-col gap-1">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.to === "/"} onClick={() => setOpen(false)}
                className={({ isActive }) => cn("px-4 py-2 rounded-lg", isActive ? "bg-secondary" : "")}>
                {l.label}
              </NavLink>
            ))}
            {!isLoading && user ? (
              <div className="flex flex-col gap-1 mt-2 pt-2 border-t border-border">
                <p className="px-4 py-1 text-xs text-muted-foreground">{user.email}</p>
                {user.role === "provider" && (
                  <Link to="/mis-espacios" onClick={() => setOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm hover:bg-secondary">
                    <HomeIcon className="w-4 h-4" /> Mis espacios
                  </Link>
                )}
                {user.role === "admin" && (
                  <Link to="/admin" onClick={() => setOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm hover:bg-secondary">
                    <LayoutDashboard className="w-4 h-4" /> Panel Admin
                  </Link>
                )}
                <button onClick={logout}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm text-destructive hover:bg-destructive/10">
                  <LogOut className="w-4 h-4" /> Cerrar sesión
                </button>
              </div>
            ) : (
              <div className="flex gap-2 mt-2">
                <Button variant="outline" className="flex-1" onClick={() => { setOpen(false); navigate("/login"); }}>
                  <User className="w-4 h-4" /> Entrar
                </Button>
                <Button variant="hero" className="flex-1" onClick={() => { setOpen(false); navigate("/registro"); }}>
                  Registrarse
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
