import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Tag, Plus, X, CalendarCheck, Pencil, ToggleLeft, ToggleRight, ImagePlus, Trash2, Star } from "lucide-react";
import {
  fetchMySpaces, updateSpaceOffer, updateSpace, createSpace, fetchIncomingReservations,
  setSchedules, uploadSpaceImage, deleteSpaceImage, setPrimaryImage,
  formatCLP, Space, DiscountType, SpaceCreatePayload, SpaceUpdatePayload, SpaceType, Schedule, SpaceImage, IncomingReservation,
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
  const [editingSpace, setEditingSpace] = useState<Space | null>(null);
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
    queryKey: ["incoming-reservations"],
    queryFn: () => fetchIncomingReservations(),
    enabled: !!me && tab === "reservations",
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
          {editingSpace && (
            <EditSpaceForm space={editingSpace} onClose={() => setEditingSpace(null)} />
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
              {spaces.map((s) => <SpaceOfferCard key={s.id} space={s} onEdit={() => setEditingSpace(s)} />)}
            </div>
          )}
        </>
      )}

      {/* Reservas recibidas */}
      {tab === "reservations" && (
        <>
          {loadingIncoming ? (
            <div className="text-center py-20 text-muted-foreground">Cargando reservas…</div>
          ) : incoming.length === 0 ? (
            <div className="text-center py-20 border border-dashed border-border rounded-2xl">
              <p className="text-muted-foreground">Aún no tienes reservas recibidas.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {incoming.map((r) => <IncomingReservationCard key={r.id} reservation={r} />)}
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
  const [schedules, setSchedules2] = useState<Omit<Schedule, "id">[]>([
    { day_of_week: 0, open_time: "08:00", close_time: "20:00" },
    { day_of_week: 1, open_time: "08:00", close_time: "20:00" },
    { day_of_week: 2, open_time: "08:00", close_time: "20:00" },
    { day_of_week: 3, open_time: "08:00", close_time: "20:00" },
    { day_of_week: 4, open_time: "08:00", close_time: "20:00" },
  ]);

  const mut = useMutation({
    mutationFn: async () => {
      const space = await createSpace(form);
      if (schedules.length > 0) await setSchedules(space.id, schedules);
      return space;
    },
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

        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-2">Horarios de disponibilidad</label>
          <ScheduleEditor value={schedules} onChange={setSchedules2} />
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

// ── Editor de horarios ────────────────────────────────────────────────────────

const DAY_NAMES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const DEFAULT_OPEN = "08:00";
const DEFAULT_CLOSE = "20:00";

interface ScheduleEditorProps {
  value: Omit<Schedule, "id">[];
  onChange: (s: Omit<Schedule, "id">[]) => void;
}

const ScheduleEditor = ({ value, onChange }: ScheduleEditorProps) => {
  const activeSet = new Set(value.map((s) => s.day_of_week));

  const toggle = (day: number) => {
    if (activeSet.has(day)) {
      onChange(value.filter((s) => s.day_of_week !== day));
    } else {
      onChange([...value, { day_of_week: day, open_time: DEFAULT_OPEN, close_time: DEFAULT_CLOSE }]);
    }
  };

  const update = (day: number, field: "open_time" | "close_time", val: string) => {
    onChange(value.map((s) => s.day_of_week === day ? { ...s, [field]: val } : s));
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5 mb-3">
        {DAY_NAMES.map((name, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => toggle(idx)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-smooth ${
              activeSet.has(idx)
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-muted-foreground hover:bg-secondary/70"
            }`}
          >
            {name}
          </button>
        ))}
      </div>
      {value.sort((a, b) => a.day_of_week - b.day_of_week).map((s) => (
        <div key={s.day_of_week} className="flex items-center gap-2 text-sm">
          <span className="w-8 text-muted-foreground font-medium">{DAY_NAMES[s.day_of_week]}</span>
          <input
            type="time"
            value={s.open_time}
            onChange={(e) => update(s.day_of_week, "open_time", e.target.value)}
            className="px-2 py-1 rounded-lg border border-border bg-background text-sm"
          />
          <span className="text-muted-foreground">–</span>
          <input
            type="time"
            value={s.close_time}
            onChange={(e) => update(s.day_of_week, "close_time", e.target.value)}
            className="px-2 py-1 rounded-lg border border-border bg-background text-sm"
          />
        </div>
      ))}
      {value.length === 0 && (
        <p className="text-xs text-muted-foreground">Sin días configurados — el espacio no tendrá horario visible.</p>
      )}
    </div>
  );
};

// ── Editor de imágenes ────────────────────────────────────────────────────────

interface ImageEditorProps {
  spaceId: string;
  images: SpaceImage[];
  onRefresh: () => void;
}

const ImageEditor = ({ spaceId, images, onRefresh }: ImageEditorProps) => {
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    setUploading(true);
    try {
      for (const file of files) {
        await uploadSpaceImage(spaceId, file, images.length === 0);
      }
      onRefresh();
    } catch {
      toast.error("No se pudo subir la imagen");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (imageId: string) => {
    try {
      await deleteSpaceImage(spaceId, imageId);
      onRefresh();
    } catch {
      toast.error("No se pudo eliminar la imagen");
    }
  };

  const handleSetPrimary = async (imageId: string) => {
    try {
      await setPrimaryImage(spaceId, imageId);
      onRefresh();
    } catch {
      toast.error("No se pudo cambiar la imagen principal");
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {images.map((img) => (
          <div key={img.id} className="relative group w-24 h-24">
            <img src={img.url} alt="" className="w-full h-full object-cover rounded-xl border border-border" />
            {img.is_primary && (
              <span className="absolute top-1 left-1 bg-primary rounded-full p-0.5">
                <Star className="w-2.5 h-2.5 text-white fill-white" />
              </span>
            )}
            <div className="absolute inset-0 bg-black/50 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1">
              {!img.is_primary && (
                <button onClick={() => handleSetPrimary(img.id)} className="p-1 rounded-full bg-white/20 hover:bg-white/40" title="Principal">
                  <Star className="w-3 h-3 text-white" />
                </button>
              )}
              <button onClick={() => handleDelete(img.id)} className="p-1 rounded-full bg-white/20 hover:bg-red-500/80" title="Eliminar">
                <Trash2 className="w-3 h-3 text-white" />
              </button>
            </div>
          </div>
        ))}
        <label className={`w-24 h-24 flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-border cursor-pointer hover:border-primary/50 transition-colors ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
          <ImagePlus className="w-5 h-5 text-muted-foreground mb-1" />
          <span className="text-xs text-muted-foreground">{uploading ? "Subiendo…" : "Añadir"}</span>
          <input type="file" accept="image/*" multiple className="hidden" onChange={handleUpload} />
        </label>
      </div>
      <p className="text-xs text-muted-foreground">Hover sobre imagen para gestionar. La principal aparece en los listados.</p>
    </div>
  );
};

// ── Editar espacio ─────────────────────────────────────────────────────────────

const EditSpaceForm = ({ space, onClose }: { space: Space; onClose: () => void }) => {
  const qc = useQueryClient();
  const [form, setForm] = useState<SpaceUpdatePayload>({
    name: space.name,
    type: space.type,
    description: space.description,
    address: space.location,
    city: space.city,
    price_per_hour: space.price,
    capacity: space.capacity,
    amenities: [...space.amenities],
  });
  const [amenityInput, setAmenityInput] = useState("");
  const [scheduleList, setScheduleList] = useState<Omit<Schedule, "id">[]>(
    space.schedules.map(({ day_of_week, open_time, close_time }) => ({ day_of_week, open_time, close_time }))
  );
  const [localImages, setLocalImages] = useState<SpaceImage[]>(space.images);

  const mut = useMutation({
    mutationFn: async () => {
      const updated = await updateSpace(space.id, form);
      await setSchedules(space.id, scheduleList);
      return updated;
    },
    onSuccess: () => {
      toast.success("Espacio actualizado");
      qc.invalidateQueries({ queryKey: ["my-spaces"] });
      qc.invalidateQueries({ queryKey: ["spaces"] });
      onClose();
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.message : "No se pudo actualizar"),
  });

  const set = (field: keyof SpaceUpdatePayload, value: any) =>
    setForm((f) => ({ ...f, [field]: value }));

  const addAmenity = () => {
    const v = amenityInput.trim();
    if (v && !(form.amenities ?? []).includes(v)) set("amenities", [...(form.amenities ?? []), v]);
    setAmenityInput("");
  };

  const removeAmenity = (a: string) =>
    set("amenities", (form.amenities ?? []).filter((x) => x !== a));

  const refreshImages = async () => {
    try {
      const { fetchSpace } = await import("@/lib/spaces");
      const fresh = await fetchSpace(space.id);
      setLocalImages(fresh.images);
    } catch { /* silencioso */ }
  };

  return (
    <div className="bg-card border border-primary/30 rounded-2xl p-6 mb-6 shadow-soft">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-lg">Editar: {space.name}</h2>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-1">Nombre *</label>
          <input
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.name ?? ""} onChange={(e) => set("name", e.target.value)}
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
            value={form.city ?? ""} onChange={(e) => set("city", e.target.value)}
          />
        </div>

        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-1">Dirección *</label>
          <input
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.address ?? ""} onChange={(e) => set("address", e.target.value)}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold mb-1">Precio por hora (CLP) *</label>
          <input
            type="number" min={1000} step={1000}
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.price_per_hour ?? 0} onChange={(e) => set("price_per_hour", Number(e.target.value))}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold mb-1">Capacidad (personas) *</label>
          <input
            type="number" min={1}
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm"
            value={form.capacity ?? 1} onChange={(e) => set("capacity", Number(e.target.value))}
          />
        </div>

        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-1">Descripción</label>
          <textarea
            rows={3}
            className="w-full px-3 py-2 rounded-xl border border-border bg-background text-sm resize-none"
            value={form.description ?? ""} onChange={(e) => set("description", e.target.value)}
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
          {(form.amenities ?? []).length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {(form.amenities ?? []).map((a) => (
                <span key={a} className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-secondary">
                  {a}
                  <button onClick={() => removeAmenity(a)}><X className="w-3 h-3" /></button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-2">Horarios de disponibilidad</label>
          <ScheduleEditor value={scheduleList} onChange={setScheduleList} />
        </div>

        <div className="sm:col-span-2">
          <label className="block text-xs font-semibold mb-2">Imágenes</label>
          <ImageEditor spaceId={space.id} images={localImages} onRefresh={refreshImages} />
        </div>
      </div>

      <div className="flex justify-end gap-2 mt-5">
        <Button variant="outline" onClick={onClose}>Cancelar</Button>
        <Button
          variant="hero"
          disabled={mut.isPending || !form.name || !form.address || !form.city}
          onClick={() => mut.mutate()}
        >
          {mut.isPending ? "Guardando…" : "Guardar cambios"}
        </Button>
      </div>
    </div>
  );
};

// ── Card gestión de oferta ────────────────────────────────────────────────────

const SpaceOfferCard = ({ space, onEdit }: { space: Space; onEdit: () => void }) => {
  const qc = useQueryClient();
  const [active, setActive] = useState(space.discountActive);
  const [type, setType] = useState<DiscountType>(space.discountType || "percentage");
  const [value, setValue] = useState<number>(space.discountValue || 10);
  const [minPeople, setMinPeople] = useState<number>(space.discountMinPeople || 2);
  const [isActive, setIsActive] = useState(space.available);

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

  const toggleActiveMut = useMutation({
    mutationFn: (next: boolean) => updateSpace(space.id, { is_active: next }),
    onSuccess: (_, next) => {
      setIsActive(next);
      toast.success(next ? "Espacio activado" : "Espacio desactivado");
      qc.invalidateQueries({ queryKey: ["my-spaces"] });
      qc.invalidateQueries({ queryKey: ["spaces"] });
    },
    onError: () => toast.error("No se pudo cambiar el estado"),
  });

  const preview = active && value ? Math.round(space.price * (1 - value / 100)) : space.price;

  return (
    <div className={`bg-card border rounded-2xl p-5 shadow-soft flex flex-col md:flex-row gap-4 ${isActive ? "border-border" : "border-border opacity-60"}`}>
      <img src={space.image} alt={space.name} className="w-full md:w-40 h-32 object-cover rounded-xl" />
      <div className="flex-1">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">{space.name}</h3>
            {!isActive && <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">Inactivo</span>}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">{formatCLP(space.price)} / hora</span>
            <button
              onClick={() => toggleActiveMut.mutate(!isActive)}
              disabled={toggleActiveMut.isPending}
              className="text-muted-foreground hover:text-foreground transition-colors"
              title={isActive ? "Desactivar espacio" : "Activar espacio"}
            >
              {isActive ? <ToggleRight className="w-5 h-5 text-primary" /> : <ToggleLeft className="w-5 h-5" />}
            </button>
            <button
              onClick={onEdit}
              className="text-muted-foreground hover:text-foreground transition-colors"
              title="Editar espacio"
            >
              <Pencil className="w-4 h-4" />
            </button>
          </div>
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

const IncomingReservationCard = ({ reservation: r }: { reservation: IncomingReservation }) => (
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
    <div className="text-right shrink-0">
      <p className="font-bold text-lg">{formatCLP(r.total)}</p>
      <p className="text-xs text-muted-foreground">subtotal {formatCLP(r.subtotal)}</p>
    </div>
  </div>
);

export default MySpaces;
