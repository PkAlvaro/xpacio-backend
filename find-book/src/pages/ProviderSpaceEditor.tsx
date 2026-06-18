import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Save, Plus, X, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import {
  useProviderSpace,
  useCreateProviderSpace,
  useUpdateProviderSpace,
  useProviderUploadImage,
  useProviderDeleteImage,
  useProviderSetPrimaryImage,
  useProviderReorderImages,
  useProviderSetSchedules,
} from "@/hooks/useProviderSpace";
import { ImageOrderManager } from "@/components/ImageOrderManager";
import type { SpaceType } from "@/types/api";

const TYPES: SpaceType[] = ["Oficina", "Cancha", "Sala", "Salón", "Estudio", "Terraza"];
const POLICIES = [
  { value: "flexible", label: "Flexible (24h)" },
  { value: "moderate", label: "Moderada (48h)" },
  { value: "strict", label: "Estricta (72h)" },
];
const DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const TABS = ["Info básica", "Imágenes", "Amenities", "Horarios"];

export default function ProviderSpaceEditor() {
  const { id } = useParams<{ id: string }>();
  const isNew = !id;
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);

  const { data: space, isLoading } = useProviderSpace(id);
  const createSpace = useCreateProviderSpace();
  const updateSpace = useUpdateProviderSpace();
  const uploadImage = useProviderUploadImage();
  const deleteImage = useProviderDeleteImage();
  const setPrimary = useProviderSetPrimaryImage();
  const reorderImages = useProviderReorderImages();
  const setSchedules = useProviderSetSchedules();

  const [form, setForm] = useState({
    name: "", type: "Oficina" as SpaceType, description: "", address: "",
    city: "Santiago", price_per_hour: 15000, capacity: 10,
    cancellation_policy: "flexible", cancellation_hours: 24,
    discount_active: false, discount_type: "", discount_value: 0,
  });
  const [amenities, setAmenities] = useState<string[]>([]);
  const [amenityInput, setAmenityInput] = useState("");
  const [scheduleState, setScheduleState] = useState(
    DAYS.map((_, i) => ({ day_of_week: i, open_time: "08:00", close_time: "22:00", enabled: true }))
  );

  const [synced, setSynced] = useState(false);
  if (space && !synced) {
    setForm({
      name: space.name,
      type: space.type,
      description: space.description ?? "",
      address: space.address,
      city: space.city,
      price_per_hour: space.price_per_hour,
      capacity: space.capacity,
      cancellation_policy: space.cancellation_policy,
      cancellation_hours: space.cancellation_hours,
      discount_active: space.discount_active ?? false,
      discount_type: space.discount_type ?? "",
      discount_value: space.discount_value ?? 0,
    });
    setAmenities(space.amenities);
    if (space.schedules.length > 0) {
      setScheduleState(DAYS.map((_, i) => {
        const found = space.schedules.find(s => s.day_of_week === i);
        return { day_of_week: i, open_time: found?.open_time ?? "08:00", close_time: found?.close_time ?? "22:00", enabled: !!found };
      }));
    }
    setSynced(true);
  }

  const field = (k: string) => ({
    value: (form as any)[k],
    onChange: (e: any) => setForm(f => ({ ...f, [k]: e.target.type === "number" ? Number(e.target.value) : e.target.value })),
  });

  const saveInfo = async () => {
    try {
      const payload = {
        ...form,
        amenities,
        discount_type: form.discount_type || undefined,
        discount_value: form.discount_value || undefined,
      };
      if (isNew) {
        const s = await createSpace.mutateAsync(payload);
        toast.success("Espacio creado");
        navigate(`/mis-espacios/${s.id}/editar`);
      } else {
        await updateSpace.mutateAsync({ id: id!, data: payload });
        toast.success("Cambios guardados");
      }
    } catch (err: any) {
      toast.error(err?.message ?? "Error al guardar");
    }
  };

  const saveSchedules = async () => {
    try {
      const enabled = scheduleState
        .filter(s => s.enabled)
        .map(({ day_of_week, open_time, close_time }) => ({ day_of_week, open_time, close_time }));
      await setSchedules.mutateAsync({ spaceId: id!, schedules: enabled });
      toast.success("Horarios actualizados");
    } catch (err: any) {
      toast.error(err?.message ?? "Error al guardar horarios");
    }
  };

  const addAmenity = () => {
    const v = amenityInput.trim();
    if (v && !amenities.includes(v)) setAmenities(a => [...a, v]);
    setAmenityInput("");
  };

  if (!isNew && isLoading) {
    return (
      <div className="container py-10 max-w-3xl space-y-4">
        <div className="h-8 bg-muted rounded animate-pulse w-1/3" />
        <div className="h-64 bg-muted rounded-2xl animate-pulse" />
      </div>
    );
  }

  const images = space?.images ?? [];

  return (
    <div className="container py-10 max-w-3xl">
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        <Link to="/mis-espacios" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="w-4 h-4" /> Mis espacios
        </Link>
        <div className="flex-1">
          <h1 className="font-display text-2xl font-bold">
            {isNew ? "Nuevo espacio" : form.name || "Editar espacio"}
          </h1>
          {!isNew && space?.slug && (
            <p className="text-xs text-muted-foreground mt-0.5">/{space.slug}</p>
          )}
        </div>
        {!isNew && (
          <a href={`/espacio/${space?.slug ?? id}`} target="_blank" rel="noopener noreferrer"
            className="text-xs text-primary hover:underline">
            Ver en portal →
          </a>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
        {TABS.map((t, i) => (
          <button key={t} onClick={() => setTab(i)}
            className={cn(
              "px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-smooth",
              tab === i ? "bg-foreground text-background" : "text-muted-foreground hover:bg-secondary"
            )}>
            {t}
          </button>
        ))}
      </div>

      {/* Tab: Info básica */}
      {tab === 0 && (
        <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold mb-1.5">Nombre del espacio *</label>
              <input {...field("name")} placeholder="Ej: Sala de Reuniones céntrica"
                className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20" />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5">Tipo *</label>
              <select {...field("type")}
                className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20">
                {TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5">Ciudad *</label>
              <input {...field("city")}
                className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20" />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold mb-1.5">Dirección *</label>
              <input {...field("address")} placeholder="Av. Providencia 1234, Providencia"
                className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20" />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5">Precio por hora (CLP) *</label>
              <input type="number" {...field("price_per_hour")} min={1000} step={1000}
                className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20" />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5">Capacidad (personas)</label>
              <input type="number" {...field("capacity")} min={1}
                className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20" />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5">Política de cancelación</label>
              <select {...field("cancellation_policy")}
                className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20">
                {POLICIES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold mb-1.5">Descripción</label>
              <textarea {...field("description")} rows={4} placeholder="Describe el espacio, qué incluye, etc."
                className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20 resize-none" />
            </div>
          </div>

          <div className="pt-2 border-t border-border">
            <h3 className="text-sm font-semibold mb-3">Descuento (opcional)</h3>
            <div className="grid sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold mb-1.5">Tipo</label>
                <select {...field("discount_type")}
                  className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20">
                  <option value="">Sin descuento</option>
                  <option value="percentage">Porcentaje</option>
                  <option value="volume">Por volumen</option>
                </select>
              </div>
              {form.discount_type && (
                <>
                  <div>
                    <label className="block text-xs font-semibold mb-1.5">Valor (%)</label>
                    <input type="number" {...field("discount_value")} min={1} max={100}
                      className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20" />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={form.discount_active}
                        onChange={e => setForm(f => ({ ...f, discount_active: e.target.checked }))}
                        className="w-4 h-4 rounded" />
                      <span className="text-sm">Activo</span>
                    </label>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="pt-2">
            <Button variant="hero" onClick={saveInfo} disabled={createSpace.isPending || updateSpace.isPending || !form.name || !form.address || !form.city}>
              <Save className="w-4 h-4" /> {isNew ? "Crear espacio" : "Guardar cambios"}
            </Button>
          </div>
        </div>
      )}

      {/* Tab: Imágenes */}
      {tab === 1 && (
        <ImageOrderManager
          spaceId={id}
          images={images}
          uploading={uploadImage.isPending}
          onUpload={async (files) => {
            for (const file of files) await uploadImage.mutateAsync({ spaceId: id!, file });
            toast.success(`${files.length} imagen${files.length > 1 ? "es" : ""} subida${files.length > 1 ? "s" : ""}`);
          }}
          onDelete={(imageId) => deleteImage.mutateAsync({ spaceId: id!, imageId })}
          onSetPrimary={(imageId) => setPrimary.mutateAsync({ spaceId: id!, imageId })}
          onReorder={(order) => reorderImages.mutateAsync({ spaceId: id!, order })}
        />
      )}

      {/* Tab: Amenities */}
      {tab === 2 && (
        <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
          <h3 className="font-semibold">Servicios incluidos</h3>
          <div className="flex gap-2">
            <input
              value={amenityInput}
              onChange={e => setAmenityInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addAmenity())}
              placeholder="Ej: Proyector, Wi-Fi, Aire acondicionado…"
              className="flex-1 px-3 py-2.5 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20"
            />
            <Button variant="outline" onClick={addAmenity}><Plus className="w-4 h-4" /></Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {amenities.map(a => (
              <span key={a} className="flex items-center gap-1.5 px-3 py-1.5 bg-secondary rounded-full text-sm">
                <Check className="w-3 h-3 text-success" />
                {a}
                <button onClick={() => setAmenities(prev => prev.filter(x => x !== a))} className="ml-0.5 hover:text-destructive">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {amenities.length === 0 && <p className="text-sm text-muted-foreground">Sin amenities aún.</p>}
          </div>
          <div className="pt-2">
            <Button variant="hero" onClick={saveInfo} disabled={updateSpace.isPending || isNew}>
              <Save className="w-4 h-4" /> Guardar amenities
            </Button>
          </div>
        </div>
      )}

      {/* Tab: Horarios */}
      {tab === 3 && (
        <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
          <h3 className="font-semibold">Horarios de disponibilidad</h3>
          <p className="text-xs text-muted-foreground">Define los días y horarios en que tu espacio puede ser reservado.</p>
          <div className="space-y-3">
            {scheduleState.map((s, i) => (
              <div key={i} className="flex items-center gap-4">
                <label className="flex items-center gap-2 w-16 cursor-pointer">
                  <input type="checkbox" checked={s.enabled}
                    onChange={e => setScheduleState(prev => prev.map((x, j) => j === i ? { ...x, enabled: e.target.checked } : x))}
                    className="w-4 h-4 rounded" />
                  <span className="text-sm font-medium">{DAYS[i]}</span>
                </label>
                {s.enabled ? (
                  <>
                    <input type="time" value={s.open_time}
                      onChange={e => setScheduleState(prev => prev.map((x, j) => j === i ? { ...x, open_time: e.target.value } : x))}
                      className="px-3 py-2 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20" />
                    <span className="text-muted-foreground text-sm">—</span>
                    <input type="time" value={s.close_time}
                      onChange={e => setScheduleState(prev => prev.map((x, j) => j === i ? { ...x, close_time: e.target.value } : x))}
                      className="px-3 py-2 rounded-xl border border-border bg-background text-sm outline-none focus:ring-2 ring-primary/20" />
                  </>
                ) : (
                  <span className="text-sm text-muted-foreground">Cerrado</span>
                )}
              </div>
            ))}
          </div>
          <div className="pt-2">
            <Button variant="hero" onClick={saveSchedules} disabled={setSchedules.isPending || isNew}>
              <Save className="w-4 h-4" /> Guardar horarios
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
