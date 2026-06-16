import { Link } from "react-router-dom";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, ShieldCheck, Zap, Tag } from "lucide-react";
import { SearchBar } from "@/components/SearchBar";
import { SpaceCard } from "@/components/SpaceCard";
import { useSpaces } from "@/hooks/useSpaces";
import { useMe } from "@/hooks/useAuth";

const Home = () => {
  const { data, isLoading } = useSpaces({ city: "Santiago", page_size: 6 });
  const featured = data?.items ?? [];
  const active = useSpaces({ page_size: 12 });
  const { data: user } = useMe();
  const publishHref = user?.role === "admin" ? "/admin/espacios/nuevo" : "/registro";
  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden gradient-warm">
        <div className="absolute inset-0 opacity-40 pointer-events-none">
          <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-primary/30 blur-3xl" />
          <div className="absolute top-40 -left-20 w-72 h-72 rounded-full bg-accent/20 blur-3xl" />
        </div>
        <div className="container relative pt-16 pb-32 md:pt-24 md:pb-40">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
            className="max-w-3xl">
            <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-card border border-border text-sm shadow-soft mb-6">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              Espacios disponibles para reservar hoy
            </span>
            <h1 className="font-display text-5xl md:text-7xl font-bold leading-[1.05] tracking-tight">
              Encuentra el espacio
              <span className="block italic font-display bg-gradient-to-r from-primary to-primary-glow bg-clip-text text-transparent">
                perfecto para ti.
              </span>
            </h1>
            <p className="mt-6 text-lg text-muted-foreground max-w-xl">
              Reserva oficinas, canchas, salas y estudios por hora. Sin contratos, sin complicaciones.
            </p>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-10 max-w-4xl">
            <SearchBar />
          </motion.div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="container -mt-16 relative z-10">
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { icon: Zap, title: "Reserva instantánea", desc: "Confirma tu espacio en segundos, sin esperas." },
            { icon: ShieldCheck, title: "Pago seguro", desc: "Transacciones protegidas con Transbank y Stripe." },
            { icon: Sparkles, title: "Espacios verificados", desc: "Cada lugar es revisado por nuestro equipo." },
          ].map((f) => (
            <div key={f.title} className="bg-card border border-border rounded-2xl p-6 shadow-soft">
              <div className="w-11 h-11 rounded-xl bg-primary/10 grid place-items-center mb-4">
                <f.icon className="w-5 h-5 text-primary" />
              </div>
              <h3 className="font-semibold mb-1">{f.title}</h3>
              <p className="text-sm text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* SPACES — Destacados / Ofertas */}
      <section className="container py-20">
        <div className="flex items-end justify-between mb-6 flex-wrap gap-4">
          <div>
            <h2 className="font-display text-3xl md:text-4xl font-bold">Explora espacios</h2>
            <p className="text-muted-foreground mt-2">Lo más popular y las mejores ofertas</p>
          </div>
          <Link to="/buscar" className="hidden md:inline-flex items-center gap-2 text-sm font-medium hover:gap-3 transition-all">
            Ver todos <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-5 gap-y-8">
          {isLoading
            ? Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="space-y-3">
                  <div className="aspect-[4/3] rounded-2xl bg-muted animate-pulse" />
                  <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
                  <div className="h-3 bg-muted rounded animate-pulse w-1/2" />
                </div>
              ))
            : featured.map((s, i) => <SpaceCard key={s.id} space={s} index={i} />)}
        </div>

        {active.isLoading ? (
          <div className="text-center py-20 text-muted-foreground">Cargando espacios…</div>
        ) : active.isError ? (
          <div className="text-center py-20 text-muted-foreground">No se pudieron cargar los espacios. ¿Está el backend en línea?</div>
        ) : active.data && active.data.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-5 gap-y-8">
            {active.data.map((s, i) => <SpaceCard key={s.id} space={s} index={i} />)}
          </div>
        ) : (
          <div className="text-center py-20 text-muted-foreground">
            {tab === "offers" ? "No hay espacios en oferta por ahora." : "Todavía no hay espacios publicados."}
          </div>
        )}
      </section>

      {/* CTA */}
      <section className="container pb-20">
        <div className="rounded-3xl gradient-hero p-10 md:p-16 text-primary-foreground relative overflow-hidden">
          <div className="absolute inset-0 opacity-20 mix-blend-overlay">
            <div className="absolute top-0 right-0 w-64 h-64 bg-white rounded-full blur-3xl" />
          </div>
          <div className="relative max-w-2xl">
            <h2 className="font-display text-3xl md:text-5xl font-bold leading-tight">
              ¿Tienes un espacio increíble?
            </h2>
            <p className="mt-4 opacity-90 text-lg">
              Conviértete en anfitrión y genera ingresos arrendando por hora.
            </p>
            <Link to={publishHref} className="inline-flex items-center gap-2 mt-6 px-6 py-3 rounded-full bg-background text-foreground font-medium hover:scale-105 transition-smooth">
              Publica tu espacio <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
