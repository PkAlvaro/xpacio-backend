import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, MapPin, Star, Users, Check, Calendar as CalIcon, DoorOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SpaceMap } from "@/components/SpaceMap";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useSpace, useAvailability, useSubSpaces, useSimilarSpaces } from "@/hooks/useSpaces";
import { SpaceCard } from "@/components/SpaceCard";
import { useCreateReservation, useInitiatePayment } from "@/hooks/useReservations";
import { useMe } from "@/hooks/useAuth";
import { useSpaceReviews } from "@/hooks/useReviews";
import ReviewList from "@/components/ReviewList";
import { ApiError } from "@/lib/api";
import type { SubSpaceItem } from "@/types/api";

const formatCLP = (n: number) =>
  new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" }).format(n);

const PLACEHOLDER = "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&q=80";

const SpaceDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: space, isLoading } = useSpace(id);
  const { data: user } = useMe();
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [start, setStart] = useState("10:00");
  const [end, setEnd] = useState("12:00");
  const [activeImg, setActiveImg] = useState(0);
  const [numPeopleStr, setNumPeopleStr] = useState("1");

  const { data: slots } = useAvailability(id, date);
  const { data: subSpaces } = useSubSpaces(id);
  const { data: similar = [], isLoading: similarLoading } = useSimilarSpaces(id);
  const { data: reviewsData, isLoading: reviewsLoading } = useSpaceReviews(id);
  const createReservation = useCreateReservation();
  const initiatePayment = useInitiatePayment();

  if (isLoading) {
    return (
      <div className="container py-20 space-y-4">
        <div className="h-10 bg-muted rounded animate-pulse w-1/2" />
        <div className="h-64 bg-muted rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (!space) return <div className="container py-20">Espacio no encontrado.</div>;

  const images = space.images.length > 0 ? space.images.map(i => i.url) : [PLACEHOLDER];
  const startMins = toMinutes(start);
  const endMins = toMinutes(end);
  const hours = Math.max(0, Math.ceil((endMins - startMins) / 60));
  const numPeople = Math.max(1, Math.min(space.capacity, parseInt(numPeopleStr, 10) || 1));
  const isVolume = space.discountType === "volume";
  const volumeApplies = isVolume && space.discountMinPeople != null && numPeople >= space.discountMinPeople;
  const effectivePrice = volumeApplies && space.discountedPrice != null
    ? space.discountedPrice
    : space.price_per_hour;
  const subtotalBase = hours * space.price_per_hour;
  const total = hours * effectivePrice;

  const slotAvailable = slots?.find(s => s.start === start)?.available ?? true;

  const reserve = async () => {
    if (!user) {
      toast.error("Inicia sesión para reservar");
      navigate("/login");
      return;
    }
    if (hours <= 0) return toast.error("El horario de fin debe ser posterior al inicio");
    if (!slotAvailable) return toast.error("El horario seleccionado no está disponible");

    try {
      const reservation = await createReservation.mutateAsync({
        space_id: space.id,
        date,
        start_time: start + ":00",
        end_time: end + ":00",
        num_people: numPeople,
      });
      toast.success("Reserva creada. Redirigiendo al pago...");
      await initiatePayment.mutateAsync(reservation.id);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Error al reservar");
    }
  };

  const busy = createReservation.isPending || initiatePayment.isPending;

  return (
    <div className="container py-6 md:py-10">
      <Link to="/buscar" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="w-4 h-4" /> Volver a resultados
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap mb-6">
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-bold">{space.name}</h1>
          <div className="flex items-center gap-3 mt-2 text-sm flex-wrap">
            <span className="flex items-center gap-1">
              <Star className="w-4 h-4 fill-foreground" /> {space.rating.toFixed(1)} ({space.review_count})
            </span>
            <span className="text-muted-foreground">·</span>
            <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {space.address}, {space.city}</span>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-[2fr_1fr] gap-3 mb-10">
        <motion.div layoutId={`img-${space.id}`} className="relative aspect-[16/10] md:aspect-auto rounded-2xl overflow-hidden">
          <img src={images[activeImg]} alt={space.name} className="w-full h-full object-cover" />
        </motion.div>
        <div className="grid grid-cols-3 md:grid-cols-1 gap-3">
          {images.map((g, i) => (
            <button key={i} onClick={() => setActiveImg(i)}
              className={cn("relative aspect-square md:aspect-[16/10] rounded-2xl overflow-hidden border-2 transition-smooth",
                activeImg === i ? "border-primary" : "border-transparent")}>
              <img src={g} alt="" className="w-full h-full object-cover" />
            </button>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_360px] gap-8">
        <div className="space-y-10 min-w-0">
          <section>
            <div className="flex items-center gap-6 pb-6 border-b border-border">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5" /> <span>Hasta {space.capacity} personas</span>
              </div>
              <div className="px-3 py-1 rounded-full bg-secondary text-sm">{space.type}</div>
            </div>
            <h2 className="font-display text-2xl font-semibold mt-6 mb-3">Sobre este espacio</h2>
            <p className="text-muted-foreground leading-relaxed">{space.description ?? "Sin descripción."}</p>
          </section>

          {space.amenities.length > 0 && (
            <section>
              <h2 className="font-display text-2xl font-semibold mb-4">Servicios incluidos</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                {space.amenities.map((a) => (
                  <div key={a} className="flex items-center gap-3 p-3 rounded-xl bg-secondary">
                    <Check className="w-4 h-4 text-success" /> <span className="text-sm">{a}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {subSpaces && subSpaces.length > 0 && (
            <section>
              <h2 className="font-display text-2xl font-semibold mb-4 flex items-center gap-2">
                <DoorOpen className="w-6 h-6" /> Salas y sub-espacios disponibles
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                {subSpaces.map((sub) => (
                  <SubSpaceCard key={sub.id} sub={sub} />
                ))}
              </div>
            </section>
          )}

          <section>
            <h2 className="font-display text-2xl font-semibold mb-4">Ubicación</h2>
            {space.lat && space.lng ? (
              <div className="rounded-2xl overflow-hidden border border-border" style={{ height: "340px" }}>
                <SpaceMap
                  lat={space.lat}
                  lng={space.lng}
                  name={space.name}
                  address={space.address}
                  height="340px"
                />
              </div>
            ) : (
              <div className="relative aspect-[16/9] rounded-2xl overflow-hidden border border-border bg-muted flex items-center justify-center text-muted-foreground text-sm">
                <MapPin className="w-4 h-4 mr-2" /> Sin coordenadas registradas
              </div>
            )}
            <p className="text-sm text-muted-foreground mt-2 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" /> {space.address}, {space.city}
            </p>
          </section>

          <section>
            <h2 className="font-display text-2xl font-semibold mb-4">Reseñas</h2>
            <ReviewList
              reviews={reviewsData?.items ?? []}
              total={reviewsData?.meta?.total ?? 0}
              isLoading={reviewsLoading}
            />
          </section>

          {/* SC-002 — Espacios similares recomendados */}
          <section>
            <h2 className="font-display text-2xl font-semibold mb-4">Espacios Similares Recomendados</h2>
            {similarLoading ? (
              <p className="text-muted-foreground text-sm">Cargando recomendaciones…</p>
            ) : similar.length === 0 ? (
              <p className="text-muted-foreground text-sm">No hay recomendaciones disponibles por ahora.</p>
            ) : (
              <div className="flex gap-5 overflow-x-auto pb-3 snap-x snap-mandatory -mx-1 px-1"
                style={{ scrollbarWidth: "thin" }}>
                {similar.map((s, i) => (
                  <div key={s.id} className="min-w-[260px] max-w-[260px] flex-shrink-0 snap-start">
                    <SpaceCard space={s} index={i} />
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <aside className="lg:sticky lg:top-24 self-start">
          <div className="bg-card border border-border rounded-2xl p-6 shadow-card">
            <div className="flex items-baseline gap-2 mb-5">
              <span className="text-2xl font-bold">{formatCLP(space.price_per_hour)}</span>
              <span className="text-muted-foreground">/ hora</span>
            </div>

            <label className="block text-xs font-semibold mb-1 flex items-center gap-1">
              <CalIcon className="w-3 h-3" /> Fecha
            </label>
            <input type="date" value={date} min={today} onChange={(e) => setDate(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-border bg-background mb-3" />

            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-xs font-semibold mb-1">Inicio</label>
                <select value={start} onChange={(e) => setStart(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-border bg-background">
                  {generateSlots().map((t) => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1">Fin</label>
                <select value={end} onChange={(e) => setEnd(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-border bg-background">
                  {generateSlots().filter(t => t > start).map((t) => <option key={t}>{t}</option>)}
                </select>
              </div>
            </div>

            <div className="mb-5">
              <label className="block text-xs font-semibold mb-1">Número de personas</label>
              <input
                type="number" min={1} max={space.capacity} value={numPeopleStr}
                onChange={(e) => setNumPeopleStr(e.target.value)}
                onBlur={() => setNumPeopleStr(String(numPeople))}
                className="w-full px-3 py-2.5 rounded-xl border border-border bg-background"
              />
              {isVolume && space.discountMinPeople != null && (
                <p className="text-xs text-muted-foreground mt-1">
                  Descuento de {Math.round(space.discountValue || 0)}% desde {space.discountMinPeople} personas
                  {volumeApplies ? " ✓ aplicado" : ""}
                </p>
              )}
            </div>

            {slots && (
              <p className={cn("text-xs mb-3", slotAvailable ? "text-success" : "text-destructive")}>
                {slotAvailable ? "✓ Horario disponible" : "✗ Horario no disponible"}
              </p>
            )}

            <Button variant="hero" size="lg" className="w-full" disabled={busy || !space.is_active} onClick={reserve}>
              {busy ? "Procesando..." : space.is_active ? "Reservar ahora" : "No disponible"}
            </Button>

            {hours > 0 && (
              <div className="mt-5 pt-5 border-t border-border space-y-2 text-sm">
                <div className="flex justify-between text-muted-foreground">
                  <span>{formatCLP(space.price_per_hour)} × {hours} hora{hours > 1 ? "s" : ""}</span>
                  <span>{formatCLP(total)}</span>
                </div>
                {total < subtotalBase && (
                  <div className="flex justify-between text-primary">
                    <span>Descuento</span>
                    <span>-{formatCLP(subtotalBase - total)}</span>
                  </div>
                )}
                <div className="flex justify-between font-semibold pt-2 border-t border-border">
                  <span>Total</span><span>{formatCLP(total)}</span>
                </div>
                <p className="text-xs text-muted-foreground">El total final lo confirma el servidor al crear la reserva.</p>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};

const PLACEHOLDER_SUB = "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=400&q=70";

function SubSpaceCard({ sub }: { sub: SubSpaceItem }) {
  return (
    <Link to={`/espacio/${sub.slug ?? sub.id}`}
      className="group block rounded-2xl border border-border bg-card hover:border-primary transition-smooth overflow-hidden">
      <div className="relative aspect-[16/9] overflow-hidden">
        <img
          src={sub.primary_image ?? PLACEHOLDER_SUB}
          alt={sub.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-smooth"
        />
        {sub.discount_active && sub.discounted_price && (
          <span className="absolute top-2 right-2 bg-destructive text-destructive-foreground text-xs font-bold px-2 py-1 rounded-full">
            Oferta
          </span>
        )}
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-1">
          <h3 className="font-semibold text-sm leading-tight">{sub.name}</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-secondary whitespace-nowrap">{sub.type}</span>
        </div>
        {sub.description && (
          <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{sub.description}</p>
        )}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-1 text-muted-foreground">
            <Users className="w-3.5 h-3.5" /> {sub.capacity}
          </div>
          <div className="text-right">
            {sub.discount_active && sub.discounted_price ? (
              <div>
                <span className="text-xs line-through text-muted-foreground mr-1">
                  {formatCLP(sub.price_per_hour)}
                </span>
                <span className="font-bold text-destructive">{formatCLP(sub.discounted_price)}</span>
              </div>
            ) : (
              <span className="font-bold">{formatCLP(sub.price_per_hour)}</span>
            )}
            <span className="text-xs text-muted-foreground">/hr</span>
          </div>
        </div>
        {sub.amenities.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {sub.amenities.slice(0, 3).map((a) => (
              <span key={a} className="text-xs bg-secondary rounded-full px-2 py-0.5">{a}</span>
            ))}
            {sub.amenities.length > 3 && (
              <span className="text-xs bg-secondary rounded-full px-2 py-0.5">+{sub.amenities.length - 3}</span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}

function toMinutes(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

function generateSlots(): string[] {
  const slots: string[] = [];
  for (let h = 7; h <= 23; h++) {
    slots.push(`${String(h).padStart(2, "0")}:00`);
    if (h < 23) slots.push(`${String(h).padStart(2, "0")}:30`);
  }
  return slots;
}

export default SpaceDetail;
