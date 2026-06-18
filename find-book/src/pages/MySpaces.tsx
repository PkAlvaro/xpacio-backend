import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Tag, Plus, X, CalendarCheck, Ban, Pencil, Images, AlertCircle } from "lucide-react";
import {
  fetchMySpaces, updateSpaceOffer, fetchIncomingReservations,
  providerCancelReservation,
  formatCLP, Space, DiscountType, IncomingReservation,
} from "@/lib/spaces";
import { ApiError } from "@/lib/api";
import { useMe } from "@/hooks/useAuth";
import { useProviderDisputes } from "@/hooks/useDisputes";
import type { DisputeItem } from "@/types/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { ImageOrderManager } from "@/components/ImageOrderManager";
import {
  useProviderSpace,
  useProviderUploadImage,
  useProviderDeleteImage,
  useProviderSetPrimaryImage,
  useProviderReorderImages,
} from "@/hooks/useProviderSpace";

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
  const [tab, setTab] = useState<"spaces" | "reservations" | "disputes">("spaces");
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
    retry: false,
  });

  const { data: incoming = [], isLoading: loadingIncoming } = useQuery({
    queryKey: ["incoming-reservations", reservationStatus],
    queryFn: () => fetchIncomingReservations(reservationStatus),
    enabled: !!me && tab === "reservations",
  });

  const { data: disputes = [], isLoading: loadingDisputes } = useProviderDisputes();

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
          <Button variant="hero" onClick={() => navigate("/mis-espacios/nuevo")}>
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
        <button
          onClick={() => setTab("disputes")}
          className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-smooth -mb-px flex items-center gap-1.5 ${
            tab === "disputes" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <AlertCircle className="w-3.5 h-3.5" /> Reclamaciones
          {disputes.filter(d => d.status === "open").length > 0 && (
            <span className="bg-destructive text-destructive-foreground text-xs px-1.5 py-0.5 rounded-full">
              {disputes.filter(d => d.status === "open").length}
            </span>
          )}
        </button>
      </div>

      {/* Mis espacios */}
      {tab === "spaces" && (
        <>
          {loadingSpaces ? (
            <div className="text-center py-20 text-muted-foreground">Cargando…</div>
          ) : spaces.length === 0 ? (
            <div className="text-center py-20 border border-dashed border-border rounded-2xl">
              <p className="text-muted-foreground mb-4">Aún no tienes espacios publicados.</p>
              <Button variant="hero" onClick={() => navigate("/mis-espacios/nuevo")}>
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

      {/* Reclamaciones */}
      {tab === "disputes" && (
        <>
          {loadingDisputes ? (
            <div className="text-center py-20 text-muted-foreground">Cargando…</div>
          ) : disputes.length === 0 ? (
            <div className="text-center py-20 border border-dashed border-border rounded-2xl">
              <p className="text-muted-foreground">No hay reclamaciones sobre tus espacios.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {disputes.map((d) => <ProviderDisputeCard key={d.id} dispute={d} />)}
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

// ── Card gestión de espacio ───────────────────────────────────────────────────

const SpaceOfferCard = ({ space }: { space: Space }) => {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [cardTab, setCardTab] = useState<"oferta" | "imagenes">("oferta");

  // Oferta state
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

  // Imágenes
  const { data: spaceDetail } = useProviderSpace(cardTab === "imagenes" ? space.id : undefined);
  const uploadImage = useProviderUploadImage();
  const deleteImage = useProviderDeleteImage();
  const setPrimary = useProviderSetPrimaryImage();
  const reorderImages = useProviderReorderImages();
  const images = spaceDetail?.images ?? [];

  return (
    <div className="bg-card border border-border rounded-2xl shadow-soft overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-border">
        <img src={space.image} alt={space.name} className="w-14 h-14 object-cover rounded-xl shrink-0" />
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold truncate">{space.name}</h3>
          <span className="text-sm text-muted-foreground">{formatCLP(space.price)} / hora</span>
        </div>
        <Button size="sm" variant="outline" onClick={() => navigate(`/mis-espacios/${space.id}/editar`)}>
          <Pencil className="w-3.5 h-3.5" /> Editar
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border px-4">
        <button
          onClick={() => setCardTab("oferta")}
          className={`px-3 py-2.5 text-xs font-medium border-b-2 -mb-px transition-smooth flex items-center gap-1.5 ${
            cardTab === "oferta" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
          }`}>
          <Tag className="w-3 h-3" /> Oferta
        </button>
        <button
          onClick={() => setCardTab("imagenes")}
          className={`px-3 py-2.5 text-xs font-medium border-b-2 -mb-px transition-smooth flex items-center gap-1.5 ${
            cardTab === "imagenes" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
          }`}>
          <Images className="w-3 h-3" /> Imágenes
          {images.length > 0 && (
            <span className="bg-primary/10 text-primary text-xs px-1.5 py-0.5 rounded-full">{images.length}</span>
          )}
        </button>
      </div>

      {/* Tab: Oferta */}
      {cardTab === "oferta" && (
        <div className="p-4 space-y-3">
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
      )}

      {/* Tab: Imágenes */}
      {cardTab === "imagenes" && (
        <div className="p-4">
          <ImageOrderManager
            spaceId={space.id}
            images={images}
            uploading={uploadImage.isPending}
            onUpload={async (files) => {
              for (const file of files) await uploadImage.mutateAsync({ spaceId: space.id, file });
              toast.success(`${files.length} imagen${files.length > 1 ? "es" : ""} subida${files.length > 1 ? "s" : ""}`);
            }}
            onDelete={(imageId) => deleteImage.mutateAsync({ spaceId: space.id, imageId })}
            onSetPrimary={(imageId) => setPrimary.mutateAsync({ spaceId: space.id, imageId })}
            onReorder={(order) => reorderImages.mutateAsync({ spaceId: space.id, order })}
          />
        </div>
      )}
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

// ── Card reclamación (vista anfitrión) ───────────────────────────────────────

const DISPUTE_STATUS_LABELS: Record<string, string> = {
  open: "Abierta",
  resolved_refund: "Reembolso",
  resolved_rejected: "Rechazada",
};

const DISPUTE_STATUS_COLORS: Record<string, string> = {
  open: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  resolved_refund: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  resolved_rejected: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
};

const ProviderDisputeCard = ({ dispute: d }: { dispute: DisputeItem }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="bg-card border border-border rounded-2xl p-5 shadow-soft">
      <div className="flex items-start gap-4 flex-wrap sm:flex-nowrap">
        <div className="flex-1 space-y-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold truncate">{d.space_name ?? "Espacio"}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${DISPUTE_STATUS_COLORS[d.status] ?? "bg-muted text-muted-foreground"}`}>
              {DISPUTE_STATUS_LABELS[d.status] ?? d.status}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            {d.opener_name ?? "Cliente"} — {d.opener_email}
          </p>
          <p className="text-sm text-muted-foreground">
            {new Date(d.created_at).toLocaleDateString("es-CL", { day: "2-digit", month: "long", year: "numeric" })}
          </p>
        </div>
        <button
          onClick={() => setOpen(v => !v)}
          className="text-xs text-primary underline underline-offset-2 shrink-0"
        >
          {open ? "Ocultar" : "Ver detalle"}
        </button>
      </div>

      {open && (
        <div className="mt-4 space-y-3 border-t border-border pt-4">
          <div>
            <p className="text-xs font-semibold text-muted-foreground mb-1">Motivo</p>
            <p className="text-sm">{d.reason}</p>
          </div>
          {d.evidence.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground mb-2">Evidencia ({d.evidence.length})</p>
              <div className="flex flex-wrap gap-2">
                {d.evidence.map(e => (
                  <a key={e.id} href={e.url} target="_blank" rel="noreferrer">
                    <img src={e.url} alt={e.filename ?? "evidencia"} className="w-20 h-20 object-cover rounded-xl border border-border" />
                  </a>
                ))}
              </div>
            </div>
          )}
          {d.admin_notes && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground mb-1">Resolución del administrador</p>
              <p className="text-sm">{d.admin_notes}</p>
            </div>
          )}
          {d.refund_amount != null && (
            <p className="text-sm">
              Reembolso: <span className="font-semibold">{d.refund_amount.toLocaleString("es-CL", { style: "currency", currency: "CLP" })}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default MySpaces;
