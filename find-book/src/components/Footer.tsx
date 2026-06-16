import { Building2 } from "lucide-react";

export const Footer = () => (
  <footer className="border-t border-border mt-20">
    <div className="container py-12 grid md:grid-cols-4 gap-8">
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg gradient-hero grid place-items-center">
            <Building2 className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-display text-lg font-bold">Xpacio</span>
        </div>
        <p className="text-sm text-muted-foreground">Arrienda espacios únicos para trabajar, jugar y celebrar.</p>
      </div>
      {[
        { title: "Compañía", items: ["Sobre nosotros", "Carreras", "Prensa", "Blog"] },
        { title: "Soporte", items: ["Centro de ayuda", "Confianza y seguridad", "Contacto"] },
        { title: "Anfitriones", items: ["Publica tu espacio", "Recursos", "Comunidad"] },
      ].map((s) => (
        <div key={s.title}>
          <h4 className="font-semibold mb-3">{s.title}</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            {s.items.map((i) => <li key={i} className="hover:text-foreground transition-smooth cursor-pointer">{i}</li>)}
          </ul>
        </div>
      ))}
    </div>
    <div className="border-t border-border">
      <div className="container py-4 text-xs text-muted-foreground flex justify-between flex-wrap gap-2">
        <span>© 2026 Xpacio. Todos los derechos reservados.</span>
        <span>Hecho con ❤ en Santiago</span>
      </div>
    </div>
  </footer>
);