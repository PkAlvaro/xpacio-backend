import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useLogin, useRegister } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";

export const Login = () => {
  const navigate = useNavigate();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login.mutateAsync({ email, password });
      toast.success("¡Sesión iniciada!");
      navigate("/");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Credenciales incorrectas");
    }
  };

  return (
    <AuthShell title="Bienvenido de vuelta" subtitle="Inicia sesión para continuar">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" type="email" placeholder="tu@email.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Contraseña" type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
        <Button type="submit" variant="hero" size="lg" className="w-full" disabled={login.isPending}>
          {login.isPending ? "Ingresando..." : "Iniciar sesión"}
        </Button>
        <p className="text-sm text-center text-muted-foreground">
          ¿No tienes cuenta? <Link to="/registro" className="text-primary font-medium hover:underline">Regístrate</Link>
        </p>
      </form>
    </AuthShell>
  );
};

export const Register = () => {
  const navigate = useNavigate();
  const register = useRegister();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isHost, setIsHost] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await register.mutateAsync({ name, email, password, role: isHost ? "provider" : "client" });
      toast.success("¡Cuenta creada!");
      navigate("/");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Error al crear cuenta");
    }
  };

  return (
    <AuthShell title="Crea tu cuenta" subtitle="Reserva espacios increíbles en segundos">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Nombre" placeholder="Juan Pérez" value={name} onChange={(e) => setName(e.target.value)} />
        <Field label="Email" type="email" placeholder="tu@email.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Contraseña" type="password" placeholder="Mínimo 8 caracteres" value={password} onChange={(e) => setPassword(e.target.value)} />
        <label className="flex items-center gap-3 p-3 rounded-xl border border-border cursor-pointer hover:bg-muted/50 transition-smooth">
          <input
            type="checkbox"
            checked={isHost}
            onChange={(e) => setIsHost(e.target.checked)}
            className="w-4 h-4 accent-primary"
          />
          <div>
            <p className="text-sm font-medium">Quiero ser anfitrión</p>
            <p className="text-xs text-muted-foreground">Publica y gestiona tus propios espacios</p>
          </div>
        </label>
        <Button type="submit" variant="hero" size="lg" className="w-full" disabled={register.isPending}>
          {register.isPending ? "Creando cuenta..." : "Crear cuenta"}
        </Button>
        <p className="text-sm text-center text-muted-foreground">
          ¿Ya tienes cuenta? <Link to="/login" className="text-primary font-medium hover:underline">Inicia sesión</Link>
        </p>
      </form>
    </AuthShell>
  );
};

const Field = ({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) => (
  <div>
    <label className="block text-sm font-medium mb-1.5">{label}</label>
    <input required {...props} className="w-full px-4 py-3 rounded-xl border border-border bg-background outline-none focus:border-primary transition-smooth" />
  </div>
);

const AuthShell = ({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) => (
  <div className="min-h-[calc(100vh-4rem)] grid place-items-center px-4 py-12 gradient-warm">
    <div className="w-full max-w-md">
      <Link to="/" className="flex items-center gap-2 justify-center mb-8">
        <div className="w-10 h-10 rounded-xl gradient-hero grid place-items-center shadow-glow">
          <Building2 className="w-5 h-5 text-primary-foreground" />
        </div>
        <span className="font-display text-2xl font-bold">Xpacio</span>
      </Link>
      <div className="bg-card rounded-3xl p-8 shadow-card border border-border">
        <h1 className="font-display text-2xl font-bold">{title}</h1>
        <p className="text-muted-foreground text-sm mt-1 mb-6">{subtitle}</p>
        {children}
      </div>
    </div>
  </div>
);
