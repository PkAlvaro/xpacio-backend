import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { MapPin, Calendar as CalIcon, Clock, Search, Locate, Star, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/api";
import type { ApiResponse } from "@/types/api";

interface SpaceSuggestion {
  id: string;
  slug?: string;
  name: string;
  type: string;
  city: string;
  address: string;
  primary_image: string | null;
  rating: number;
  price_per_hour: number;
}

const formatCLP = (n: number) =>
  new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(n);

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export const SearchBar = ({ compact = false }: { compact?: boolean }) => {
  const navigate = useNavigate();
  const today = new Date().toISOString().slice(0, 10);
  const [location, setLocation] = useState("Santiago");
  const [date, setDate] = useState(today);
  const [time, setTime] = useState("10:00");
  const [nameQuery, setNameQuery] = useState("");
  const [suggestions, setSuggestions] = useState<SpaceSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const nameRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const debouncedQuery = useDebounce(nameQuery, 250);

  useEffect(() => {
    if (!debouncedQuery || debouncedQuery.length < 2) {
      setSuggestions([]);
      return;
    }
    setLoadingSuggestions(true);
    apiRequest<ApiResponse<SpaceSuggestion[]>>(`/spaces/suggest?q=${encodeURIComponent(debouncedQuery)}&limit=8`)
      .then((res) => { setSuggestions(res.data); setShowSuggestions(true); })
      .catch(() => setSuggestions([]))
      .finally(() => setLoadingSuggestions(false));
  }, [debouncedQuery]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
        nameRef.current && !nameRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const geo = () => {
    if (!navigator.geolocation) return toast.error("Geolocalización no disponible");
    toast.loading("Detectando tu ubicación...");
    navigator.geolocation.getCurrentPosition(
      () => { toast.dismiss(); toast.success("Ubicación detectada: Santiago"); setLocation("Cerca de mí"); },
      () => { toast.dismiss(); toast.error("No pudimos detectar tu ubicación"); },
    );
  };

  const submit = () => {
    const params = new URLSearchParams({ location, date, time });
    if (nameQuery) params.set("q", nameQuery);
    navigate(`/buscar?${params.toString()}`);
  };

  const pickSuggestion = (s: SpaceSuggestion) => {
    setShowSuggestions(false);
    setNameQuery(s.name);
    navigate(`/espacio/${s.slug ?? s.id}`);
  };

  return (
    <div className="relative">
      <form
        onSubmit={(e) => { e.preventDefault(); submit(); }}
        className={cn(
          "bg-card rounded-3xl shadow-card border border-border p-2 grid gap-2 md:gap-0 md:p-1.5",
          compact
            ? "md:grid-cols-[1fr_1fr_1fr_1fr_auto]"
            : "md:grid-cols-[1.2fr_1.2fr_1fr_1fr_auto]"
        )}
      >
        {/* Nombre del espacio */}
        <div className="md:px-5 md:py-3 px-4 py-3 rounded-2xl hover:bg-secondary transition-smooth relative">
          <label className="text-xs font-semibold flex items-center gap-1">
            <Building2 className="w-3 h-3" /> Espacio
          </label>
          <input
            ref={nameRef}
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
            onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
            className="bg-transparent w-full outline-none text-sm placeholder:text-muted-foreground"
            placeholder="¿Qué tipo de espacio?"
            autoComplete="off"
          />
          {loadingSuggestions && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          )}
        </div>

        {/* Ubicación */}
        <div className="md:px-5 md:py-3 px-4 py-3 rounded-2xl hover:bg-secondary transition-smooth md:border-l border-border">
          <label className="text-xs font-semibold flex items-center gap-1"><MapPin className="w-3 h-3" /> Ubicación</label>
          <div className="flex items-center gap-2">
            <input value={location} onChange={(e) => setLocation(e.target.value)}
              className="bg-transparent w-full outline-none text-sm placeholder:text-muted-foreground" placeholder="¿Dónde?" />
            <button type="button" onClick={geo} className="text-primary hover:text-primary-glow" aria-label="Usar mi ubicación">
              <Locate className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Fecha */}
        <div className="md:px-5 md:py-3 px-4 py-3 rounded-2xl hover:bg-secondary transition-smooth md:border-l border-border">
          <label className="text-xs font-semibold flex items-center gap-1"><CalIcon className="w-3 h-3" /> Fecha</label>
          <input type="date" value={date} min={today} onChange={(e) => setDate(e.target.value)}
            className="bg-transparent w-full outline-none text-sm" />
        </div>

        {/* Horario */}
        <div className="md:px-5 md:py-3 px-4 py-3 rounded-2xl hover:bg-secondary transition-smooth md:border-l border-border">
          <label className="text-xs font-semibold flex items-center gap-1"><Clock className="w-3 h-3" /> Horario</label>
          <input type="time" value={time} onChange={(e) => setTime(e.target.value)}
            className="bg-transparent w-full outline-none text-sm" />
        </div>

        <div className="md:p-1.5 p-1">
          <Button type="submit" variant="hero" size="lg" className="w-full md:w-auto rounded-2xl h-full md:px-6">
            <Search className="w-4 h-4" /> Buscar
          </Button>
        </div>
      </form>

      {/* Dropdown de sugerencias */}
      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute top-full left-0 right-0 mt-2 bg-card border border-border rounded-2xl shadow-card z-50 overflow-hidden"
        >
          <div className="p-2 text-xs text-muted-foreground font-semibold px-4 pt-3 pb-1">
            Espacios sugeridos
          </div>
          {suggestions.map((s) => (
            <button
              key={s.id}
              type="button"
              onMouseDown={(e) => { e.preventDefault(); pickSuggestion(s); }}
              className="w-full flex items-center gap-3 px-4 py-3 hover:bg-secondary transition-smooth text-left"
            >
              <div className="w-12 h-12 rounded-xl overflow-hidden bg-muted shrink-0">
                {s.primary_image ? (
                  <img src={s.primary_image} alt={s.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Building2 className="w-5 h-5 text-muted-foreground" />
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm truncate">{s.name}</p>
                <p className="text-xs text-muted-foreground truncate">{s.address}, {s.city}</p>
                <div className="flex items-center gap-3 mt-0.5">
                  <span className="text-xs bg-secondary rounded-full px-2 py-0.5">{s.type}</span>
                  <span className="text-xs flex items-center gap-1">
                    <Star className="w-3 h-3 fill-foreground" /> {s.rating.toFixed(1)}
                  </span>
                </div>
              </div>
              <div className="text-right shrink-0">
                <p className="font-bold text-sm">{formatCLP(s.price_per_hour)}</p>
                <p className="text-xs text-muted-foreground">/hr</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
