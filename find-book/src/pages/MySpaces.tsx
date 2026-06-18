import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Tag, Plus, X, CalendarCheck, Ban } from "lucide-react";
import {
  fetchMySpaces, updateSpaceOffer, createSpace, fetchIncomingReservations,
  providerCancelReservation,
  formatCLP, Space, DiscountType, SpaceCreatePayload, SpaceType, IncomingReservation,
} from "@/lib/spaces";
import { ApiError } from "@/lib/api";
import { useMe } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const SPACE_TYPES: SpaceType[] = ["Oficina", "Cancha", "Sala", "Salón", "Estudio", "Terraza"];

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  confirmed: "Confirmada",
  cancelled: "Cancelada",
  completed: "Completada",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  confirmed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  cancelled: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  completed: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
};

const MySpaces = () => {
  const navigate = useNavigate();
  const [tab, setTab] = useState<"spaces" | "reservations">("spaces");
  const [showCreate, setShowCreate] = useState(false);
  const [reservationStatus, setReservationStatus] = useState<string | undefined>(undefined);
  const { data: me, isLoading: meLoading } = useMe();

  useEffect(() => {
    if (meLoading) return;
    if (!me) {
      navigate("/login");
    } else if (me.role !== "provider" && me.role !== "admin") {
      toast.error("Necesitas una cuenta de anfitrión");
      navigate("/");
    }
  }, [me, meLoading, navigate]);

  const { data: spaces = [], isLoading: loadingSpaces } = useQuery({
    queryKey: ["my-spaces"],
    queryFn: fetchMySpaces,
    enabled: !!me,
  });

  const { data: incoming = [], isLoading: loadingIncoming } = useQuery({
    queryKey: ["incoming-reservations", reservationStatus],
    queryFn: () => fetchIncomingReservations(reservationStatus),
    enabled: !!me && tab === "reservations",
  });

  const qc = useQueryClient();
  const cancelMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      providerCancelReservation(id, reason),
    onSuccess: () => {
      toast.success("Reserva cancelada");
      qc.invalidateQueries({ queryKey: ["incoming-reservations"] });
    },
    onError: () => toast.error("No se pudo cancelar la reserva"),
  });

  return (
    <div className="container py-10 max-w-5xl">
      <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
        <h1 className="font-display text-3xl md:text-4xl font-bold">Panel de anfitrión</h1>
        {tab === "spaces" && (
          <Button variant="hero" onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4" /> Crear espacio
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-8 border-b border-border">
        <button
          onClick={() => setTab("spaces")}
          className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-smooth -mb-px ${
            tab === "spaces" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Mis espacios
        </button>
        <button
          onClick={() => setTab("reservations")}
          className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-smooth -mb-px flex items-center gap-1.5 ${
            tab === "reservations" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <CalendarCheck className="w-3.5 h-3.5" /> Reservas recibidas
        </button>
      </div>

      {/* Mis espacios */}
      {tab === "spaces" && (
        <>
          {showCreate && (
            <CreateSpaceForm onClose={() => setShowCreate(false)} />
          )}
          {loadingSpaces ? (
            <div className="text-center py-20 text-muted-foreground">Cargando…</div>
          ) : spaces.length === 0 && !showCreate ? (
            <div className="text-center py-20 border border-dashed border-border rounded-2xl">
              <p className="text-muted-foreground mb-4">Aún no tienes espacios publicados.</p>
              <Button variant="hero" onClick={() => setShowCreate(true)}>
                <Plus className="w-4 h-4" /> Crear tu primer espacio
              </Button>
            </div>
          ) : (
            <div className="space-y-5">
              {spaces.map((s) => <SpaceOfferCard key={s.id} space={s} />)}
            </div>
          )}
        </>
      )}

      {/* Reservas recibidas */}
      {tab === "reservations" && (
        <>
          <div className="flex gap-1 mb-5 flex-wrap">
            {([
              [undefined, "Todas"],
              ["pending", "Pendientes"],
              ["confirmed", "Confirmadas"],
              ["cancelled", "Canceladas"],
              ["completed", "Completadas"],
            ] as const).map(([val, label]) => (
              <button
                key={label}
                onClick={() => setReservationStatus(val)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-smooth border ${
                  reservationStatus === val
                    ? "bg-foreground text-background border-foreground"
                    : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {loadingIncoming ? (
            <div className="text-center py-20 text-muted-foreground">Cargando reservas…</div>
          ) : incoming.length === 0 ? (
            <div className="text-center py-20 border border-dashed border-border rounded-2xl">
              <p className="text-muted-foreground">No hay reservas{reservationStatus ? ` con estado "${STATUS_LABELS[reservationStatus]}"` : ""}.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {incoming.map((r) => (
                <IncomingReservationCard
                  key={r.id}
                  reservation={r}
                  onCancel={(id) => cancelMut.mutate({ id })}
                  cancelling={cancelMut.isPending}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ── Crear espacio ──────────────────────────────────────────────────────────────

const CreateSpaceForm = ({ onClose }: { onClose: () => void }) => {
  const qc = useQueryClient();
  const [form, setForm] = useState<SpaceCreatePayload>({
    name: "",
    type: "Oficina",
    description: "",
    address: "",
    city: "",
    price_per_hour: 10000,
    capacity: 1,
    amenities: [],
  });
  const [amenityInput, setAmenityInput] = useState("");

  const mut = useMutation({
    mutationFn: () => createSpace(form),
    onSuccess: () => {
      toast.success("Espacio creado correctamente");
      qc.invalidateQueries({ queryKey: ["my-spaces"] });
      qc.invalidateQueries({ queryKey: ["spaces"] });
      onClose();
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.message : "No se pudo crear el espacio"),
  });

  const set = (field: keyof SpaceCreatePayload, value: any) =>
    setForm((f) => ({ ...f, [field]: value }));

  const addAmenity = () => {
    const v = amenityInput.trim();
    if (v && !form.amenities.includes(v)) {
      set("amenities", [...form.amenities, v]);
    }
    setAmenityInput("");
  };

  const removeAmenity = (a: string) =>
    set("amenities", form.amenities.filter((x) => x !== a));

  return (
    <div className="bg-card border border-border rounded-2xl p-6 mb-6 shadow-soft">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-lg">Nuevo espacio</h2>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-1">Nombre *</label>
          <input
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.name} onChange={(e) => set("name", e.target.value)}
            placeholder="Ej: Sala de reuniones céntrica"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold mb-1">Tipo *</label>
          <select
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.type} onChange={(e) => set("type", e.target.value as SpaceType)}
          >
            {SPACE_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold mb-1">Ciudad *</label>
          <input
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.city} onChange={(e) => set("city", e.target.value)}
            placeholder="Santiago"
          />
        </div>

        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-1">Dirección *</label>
          <input
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.address} onChange={(e) => set("address", e.target.value)}
            placeholder="Av. Providencia 1234, Providencia"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold mb-1">Precio por hora (CLP) *</label>
          <input
            type="number" min={1000} step={1000}
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.price_per_hour} onChange={(e) => set("price_per_hour", Number(e.target.value))}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold mb-1">Capacidad (personas) *</label>
          <input
            type="number" min={1}
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.capacity} onChange={(e) => set("capacity", Number(e.target.value))}
          />
        </div>

        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-1">Descripción</label>
          <textarea
            rows={3}
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm resize-none"
            value={form.description} onChange={(e) => set("description", e.target.value)}
            placeholder="Describe el espacio, qué incluye, etc."
          />
        </div>

        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-1">Comodidades</label>
          <div className="flex gap-2 mb-2">
            <input
              className="flex-1 px-3 py-2 rounded-xl border border-border bg-background text-sm"
              value={amenityInput} onChange={(e) => setAmenityInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addAmenity())}
              placeholder="WiFi, Proyector, Estacionamiento…"
            />
            <Button type="button" variant="outline" size="sm" onClick={addAmenity}>Agregar</Button>
          </div>
          {form.amenities.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {form.amenities.map((a) => (
                <span key={a} className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-secondary">
                  {a}
                  <button onClick={() => removeAmenity(a)}><X className="w-3 h-3" /></button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-end gap-2 mt-5">
        <Button variant="outline" onClick={onClose}>Cancelar</Button>
        <Button
          variant="hero"
          disabled={mut.isPending || !form.name || !form.address || !form.city}
          onClick={() => mut.mutate()}
        >
          {mut.isPending ? "Creando…" : "Crear espacio"}
        </Button>
      </div>
    </div>
  );
};

// ── Card gestión de oferta ────────────────────────────────────────────────────

const SpaceOfferCard = ({ space }: { space: Space }) => {
  const qc = useQueryClient();
  const [active, setActive] = useState(space.discountActive);
  const [type, setType] = useState<DiscountType>(space.discountType || "percentage");
  const [value, setValue] = useState<number>(space.discountValue || 10);
  const [minPeople, setMinPeople] = useState<number>(space.discountMinPeople || 2);

  const mut = useMutation({
    mutationFn: () =>
      updateSpaceOffer(space.id, {
        discount_active: active,
        discount_type: active ? type : null,
        discount_value: active ? value : null,
        discount_min_people: active && type === "volume" ? minPeople : null,
      }),
    onSuccess: () => {
      toast.success("Oferta actualizada");
      qc.invalidateQueries({ queryKey: ["my-spaces"] });
      qc.invalidateQueries({ queryKey: ["spaces"] });
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.message : "No se pudo guardar"),
  });

  const preview = active && value ? Math.round(space.price * (1 - value / 100)) : space.price;

  return (
    <div className="bg-card border border-border rounded-2xl p-5 shadow-soft flex flex-col md:flex-row gap-4">
      <img src={space.image} alt={space.name} className="w-full md:w-40 h-32 object-cover rounded-xl" />
      <div className="flex-1">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <h3 className="font-semibold">{space.name}</h3>
          <span className="text-sm text-muted-foreground">{formatCLP(space.price)} / hora</span>
        </div>

        <div className="mt-4 space-y-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)}
              className="w-4 h-4 rounded accent-primary" />
            <span className="text-sm font-medium inline-flex items-center gap-1">
              <Tag className="w-3.5 h-3.5" /> Oferta activa
            </span>
          </label>

          {active && (
            <div className="grid sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold mb-1">Tipo de descuento</label>
                <select value={type} onChange={(e) => setType(e.target.value as DiscountType)}
                  className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm">
                  <option value="percentage">Porcentaje</option>
                  <option value="volume">Por volumen</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1">Valor (%)</label>
                <input type="number" min={1} max={100} value={value}
                  onChange={(e) => setValue(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm" />
              </div>
              {type === "volume" && (
                <div>
                  <label className="block text-xs font-semibold mb-1">Mín. personas</label>
                  <input type="number" min={1} value={minPeople}
                    onChange={(e) => setMinPeople(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm" />
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between gap-3 pt-1">
            <p className="text-sm text-muted-foreground">
              {active ? (
                <>Precio con oferta: <span className="line-through mr-1">{formatCLP(space.price)}</span>
                  <span className="font-semibold text-primary">{formatCLP(preview)}</span>
                  {type === "volume" && <span> (desde {minPeople} personas)</span>}
                </>
              ) : "Sin oferta activa"}
            </p>
            <Button size="sm" variant="hero" disabled={mut.isPending} onClick={() => mut.mutate()}>
              {mut.isPending ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Card reserva entrante ─────────────────────────────────────────────────────

const IncomingReservationCard = ({
  reservation: r,
  onCancel,
  cancelling,
}: {
  reservation: IncomingReservation;
  onCancel: (id: string) => void;
  cancelling: boolean;
}) => {
  const canCancel = r.status === "pending" || r.status === "confirmed";

  return (
    <div className="bg-card border border-border rounded-2xl p-5 shadow-soft flex flex-col sm:flex-row sm:items-center gap-4">
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold">{r.space_name ?? "Espacio"}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[r.status] ?? "bg-muted text-muted-foreground"}`}>
            {STATUS_LABELS[r.status] ?? r.status}
          </span>
        </div>
        <p className="text-sm text-muted-foreground">
          {r.client_name ?? "Cliente"} &mdash; {r.client_email}
        </p>
        <p className="text-sm">
          {new Date(r.date).toLocaleDateString("es-CL", { day: "2-digit", month: "long", year: "numeric" })}
          {" · "}{r.start_time.slice(0, 5)} – {r.end_time.slice(0, 5)}
          {" · "}{r.hours}h · {r.num_people} persona{r.num_people !== 1 ? "s" : ""}
        </p>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <div className="text-right">
          <p className="font-bold text-lg">{formatCLP(r.total)}</p>
          <p className="text-xs text-muted-foreground">subtotal {formatCLP(r.subtotal)}</p>
        </div>
        {canCancel && (
          <button
            onClick={() => {
              if (confirm(`¿Cancelar la reserva de ${r.client_name ?? "este cliente"}?`)) {
                onCancel(r.id);
              }
            }}
            disabled={cancelling}
            title="Cancelar reserva"
            className="p-2 rounded-xl hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-smooth disabled:opacity-50"
          >
            <Ban className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};

export default MySpaces;
