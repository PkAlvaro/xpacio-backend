import { useCallback, useRef } from "react";
import { GoogleMap, Marker, useJsApiLoader, InfoWindow } from "@react-google-maps/api";

const API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;

const MAP_OPTIONS: google.maps.MapOptions = {
  disableDefaultUI: false,
  zoomControl: true,
  streetViewControl: false,
  mapTypeControl: false,
  fullscreenControl: true,
  styles: [
    { featureType: "poi", elementType: "labels", stylers: [{ visibility: "off" }] },
  ],
};

interface Pin {
  id: string;
  lat: number;
  lng: number;
  label?: string;
}

interface SpaceMapProps {
  lat: number;
  lng: number;
  name: string;
  address: string;
  pins?: Pin[];
  height?: string;
  onPinClick?: (id: string) => void;
}

export function SpaceMap({ lat, lng, name, address, pins, height = "100%", onPinClick }: SpaceMapProps) {
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: API_KEY,
    id: "xpacio-google-map",
  });

  const mapRef = useRef<google.maps.Map | null>(null);
  const onLoad = useCallback((map: google.maps.Map) => { mapRef.current = map; }, []);
  const onUnmount = useCallback(() => { mapRef.current = null; }, []);

  if (loadError) {
    const msg = loadError.message || String(loadError);
    return (
      <div className="w-full flex flex-col items-center justify-center gap-2 bg-muted rounded-2xl text-muted-foreground text-sm p-4" style={{ height }}>
        <span className="font-semibold text-destructive">Error al cargar Google Maps</span>
        <span className="text-xs text-center max-w-sm opacity-70">{msg}</span>
        {!API_KEY && <span className="text-xs text-destructive">VITE_GOOGLE_MAPS_API_KEY no está definida</span>}
      </div>
    );
  }

  if (!isLoaded) {
    return <div className="w-full bg-muted rounded-2xl animate-pulse" style={{ height }} />;
  }

  const center = { lat, lng };

  return (
    <GoogleMap
      mapContainerStyle={{ width: "100%", height, borderRadius: "1rem" }}
      center={center}
      zoom={15}
      options={MAP_OPTIONS}
      onLoad={onLoad}
      onUnmount={onUnmount}
    >
      {/* Pin principal del espacio */}
      <Marker
        position={center}
        title={name}
        icon={{
          path: google.maps.SymbolPath.CIRCLE,
          scale: 10,
          fillColor: "#f97316",
          fillOpacity: 1,
          strokeColor: "#ffffff",
          strokeWeight: 2,
        }}
      />

      {/* Pins adicionales (buscador) */}
      {pins?.map((p) => (
        <Marker
          key={p.id}
          position={{ lat: p.lat, lng: p.lng }}
          label={p.label ? { text: p.label, color: "#fff", fontSize: "11px", fontWeight: "bold" } : undefined}
          icon={{
            path: google.maps.SymbolPath.CIRCLE,
            scale: 8,
            fillColor: "#f97316",
            fillOpacity: 0.9,
            strokeColor: "#ffffff",
            strokeWeight: 2,
          }}
          onClick={() => onPinClick?.(p.id)}
          cursor={onPinClick ? "pointer" : "default"}
        />
      ))}
    </GoogleMap>
  );
}
