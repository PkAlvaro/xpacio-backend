import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom"; // useNavigate used in SearchMapView
import { motion, AnimatePresence } from "framer-motion";
import { LayoutList, Map as MapIcon, SlidersHorizontal, LocateFixed, Loader2 } from "lucide-react";
import { SearchBar } from "@/components/SearchBar";
import { SpaceCard } from "@/components/SpaceCard";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { SpaceMap } from "@/components/SpaceMap";
import { cn } from "@/lib/utils";
import { useSpaces } from "@/hooks/useSpaces";
import { toast } from "sonner";
import type { SpaceType, SpaceListItem } from "@/types/api";

const formatCLP = (n: number) => new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" }).format(n);
const TYPES: SpaceType[] = ["Oficina", "Cancha", "Sala", "Salón", "Estudio", "Terraza"];

const Search = () => {
  const [params] = useSearchParams();
  const [view, setView] = useState<"list" | "map">("list");
  const [showFilters, setShowFilters] = useState(true);
  const [maxPrice, setMaxPrice] = useState(50000);
  const [minCapacity, setMinCapacity] = useState(1);
  const [selectedType, setSelectedType] = useState<SpaceType | undefined>();
  const [userLat, setUserLat] = useState<number | undefined>();
  const [userLng, setUserLng] = useState<number | undefined>();
  const [locating, setLocating] = useState(false);

  const city = params.get("location") || undefined;
  const nameQ = params.get("q") || undefined;

  const handleNearMe = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocalización no disponible en este navegador");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLat(pos.coords.latitude);
        setUserLng(pos.coords.longitude);
        setLocating(false);
        toast.success("Mostrando espacios cercanos a tu ubicación");
      },
      () => {
        setLocating(false);
        toast.error("No se pudo obtener tu ubicación");
      },
      { timeout: 8000 }
    );
  };

  const { data, isLoading } = useSpaces({
    city: userLat ? undefined : city,
    q: nameQ,
    type: selectedType,
    max_price: maxPrice,
    min_capacity: minCapacity > 1 ? minCapacity : undefined,
    lat: userLat,
    lng: userLng,
    radius_km: userLat ? 10 : undefined,
  });

  const spaces = data?.items ?? [];

  return (
    <div>
      <div className="border-b border-border bg-card sticky top-16 z-30">
        <div className="container py-4">
          <SearchBar compact />
        </div>
      </div>

      <div className="container py-8">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="font-display text-2xl md:text-3xl font-bold">
              {isLoading ? "Buscando..." : `${spaces.length} espacios en ${city || "Santiago"}`}
            </h1>
            <p className="text-sm text-muted-foreground">
              {params.get("date") || "Hoy"} · {params.get("time") || "Cualquier hora"}
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button variant="outline" onClick={handleNearMe} disabled={locating}>
              {locating ? <Loader2 className="w-4 h-4 animate-spin" /> : <LocateFixed className="w-4 h-4" />}
              {userLat ? "Cerca de mí ✓" : "Cerca de mí"}
            </Button>
            {userLat && (
              <Button variant="ghost" size="sm" onClick={() => { setUserLat(undefined); setUserLng(undefined); }}>
                Limpiar ubicación
              </Button>
            )}
            <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
              <SlidersHorizontal className="w-4 h-4" /> Filtros
            </Button>
            <div className="flex bg-secondary rounded-full p-1">
              <button onClick={() => setView("list")}
                className={cn("px-4 py-1.5 rounded-full text-sm font-medium transition-smooth flex items-center gap-1.5",
                  view === "list" && "bg-card shadow-soft")}>
                <LayoutList className="w-4 h-4" /> Lista
              </button>
              <button onClick={() => setView("map")}
                className={cn("px-4 py-1.5 rounded-full text-sm font-medium transition-smooth flex items-center gap-1.5",
                  view === "map" && "bg-card shadow-soft")}>
                <MapIcon className="w-4 h-4" /> Mapa
              </button>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-[280px_1fr] gap-8">
          <AnimatePresence>
            {showFilters && (
              <motion.aside initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
                className="space-y-6 lg:sticky lg:top-44 self-start">
                <div>
                  <h3 className="font-semibold mb-3">Precio máximo</h3>
                  <Slider value={[maxPrice]} min={5000} max={50000} step={1000}
                    onValueChange={(v) => setMaxPrice(v[0])} />
                  <p className="text-sm text-muted-foreground mt-2">{formatCLP(maxPrice)} / hora</p>
                </div>
                <div>
                  <h3 className="font-semibold mb-3">Capacidad mínima</h3>
                  <Slider value={[minCapacity]} min={1} max={50} step={1}
                    onValueChange={(v) => setMinCapacity(v[0])} />
                  <p className="text-sm text-muted-foreground mt-2">{minCapacity === 1 ? "Sin mínimo" : `${minCapacity} personas`}</p>
                </div>
                <div>
                  <h3 className="font-semibold mb-3">Tipo de espacio</h3>
                  <div className="flex flex-wrap gap-2">
                    {TYPES.map((t) => (
                      <button key={t}
                        onClick={() => setSelectedType(selectedType === t ? undefined : t)}
                        className={cn("px-3 py-1.5 rounded-full text-sm border transition-smooth",
                          selectedType === t ? "bg-foreground text-background border-foreground" : "border-border hover:border-foreground")}>
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
              </motion.aside>
            )}
          </AnimatePresence>

          <div className={cn(!showFilters && "lg:col-span-2")}>
            {isLoading && (
              <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-x-5 gap-y-8">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="aspect-[4/3] rounded-2xl bg-muted animate-pulse" />
                ))}
              </div>
            )}

            {!isLoading && view === "list" && (
              <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-x-5 gap-y-8">
                {spaces.map((s, i) => <SpaceCard key={s.id} space={s} index={i} />)}
              </div>
            )}

            {!isLoading && view === "map" && <SearchMapView spaces={spaces} />}

            {!isLoading && spaces.length === 0 && (
              <div className="text-center py-20 text-muted-foreground">
                No encontramos espacios con esos filtros.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

function SearchMapView({ spaces }: { spaces: SpaceListItem[] }) {
  const navigate = useNavigate();
  const withCoords = spaces.filter(s => s.lat && s.lng);
  const centerLat = withCoords.length
    ? withCoords.reduce((acc, s) => acc + s.lat!, 0) / withCoords.length
    : -33.4489;
  const centerLng = withCoords.length
    ? withCoords.reduce((acc, s) => acc + s.lng!, 0) / withCoords.length
    : -70.6693;

  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-4">
      <div className="rounded-2xl overflow-hidden border border-border lg:h-[70vh] h-[50vw]">
        <SpaceMap
          lat={centerLat}
          lng={centerLng}
          name=""
          address=""
          height="100%"
          pins={withCoords.map(s => ({
            id: s.id,
            lat: s.lat!,
            lng: s.lng!,
            label: new Intl.NumberFormat("es-CL", { notation: "compact", maximumFractionDigits: 0 }).format(s.price_per_hour),
          }))}
          onPinClick={(id) => navigate(`/espacio/${id}`)}
        />
      </div>
      <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
        {spaces.map((s, i) => <SpaceCard key={s.id} space={s} index={i} />)}
      </div>
    </div>
  );
}

export default Search;
