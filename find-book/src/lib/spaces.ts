import { apiRequest } from "@/lib/api";
import office from "@/assets/space-office.jpg";
import court from "@/assets/space-court.jpg";
import meeting from "@/assets/space-meeting.jpg";
import hall from "@/assets/space-hall.jpg";
import studio from "@/assets/space-studio.jpg";
import rooftop from "@/assets/space-rooftop.jpg";

export type SpaceType = "Oficina" | "Cancha" | "Sala" | "Salón" | "Estudio" | "Terraza";
export type DiscountType = "percentage" | "volume";

// Imagen de respaldo por tipo cuando el espacio no tiene imágenes cargadas
const FALLBACK_BY_TYPE: Record<string, string> = {
  Oficina: office,
  Cancha: court,
  Sala: meeting,
  Salón: hall,
  Estudio: studio,
  Terraza: rooftop,
};
const FALLBACKS = [office, court, meeting, hall, studio, rooftop];

function fallbackImage(type: string, id: string): string {
  if (FALLBACK_BY_TYPE[type]) return FALLBACK_BY_TYPE[type];
  // determinístico por id
  let sum = 0;
  for (const c of id) sum += c.charCodeAt(0);
  return FALLBACKS[sum % FALLBACKS.length];
}

// ── Tipo de dominio usado por el frontend ───────────────────────────────
export interface Space {
  id: string;
  name: string;
  type: SpaceType;
  location: string; // dirección
  city: string;
  price: number; // CLP por hora (precio base)
  rating: number;
  reviews: number;
  capacity: number;
  available: boolean;
  image: string;
  gallery: string[];
  description: string;
  amenities: string[];
  lat: number | null;
  lng: number | null;
  distanceKm?: number | null;
  // SC-001 — descuentos
  discountActive: boolean;
  discountType: DiscountType | null;
  discountValue: number | null;
  discountMinPeople: number | null;
  discountedPrice: number | null; // precio/hora con descuento aplicado
}

// ── Tipos crudos del backend ────────────────────────────────────────────
interface ApiSpace {
  id: string;
  name: string;
  type: SpaceType;
  city: string;
  address?: string;
  location?: string;
  description?: string | null;
  lat: number | null;
  lng: number | null;
  price_per_hour: number;
  capacity: number;
  rating: number;
  review_count: number;
  is_active: boolean;
  primary_image?: string | null;
  images?: { url: string; is_primary: boolean }[];
  amenities?: string[];
  distance_km?: number | null;
  discount_active?: boolean;
  discount_type?: DiscountType | null;
  discount_value?: number | null;
  discount_min_people?: number | null;
  discounted_price?: number | null;
}

export function mapSpace(s: ApiSpace): Space {
  const galleryUrls = (s.images || []).map((i) => i.url).filter(Boolean);
  const primary = s.primary_image || galleryUrls[0] || fallbackImage(s.type, s.id);
  const gallery = galleryUrls.length ? galleryUrls : [primary];
  return {
    id: s.id,
    name: s.name,
    type: s.type,
    location: s.address || s.location || s.city,
    city: s.city,
    price: s.price_per_hour,
    rating: Number(s.rating) || 0,
    reviews: s.review_count ?? 0,
    capacity: s.capacity,
    available: s.is_active,
    image: primary,
    gallery,
    description: s.description || "",
    amenities: s.amenities || [],
    lat: s.lat != null ? Number(s.lat) : null,
    lng: s.lng != null ? Number(s.lng) : null,
    distanceKm: s.distance_km ?? null,
    discountActive: !!s.discount_active,
    discountType: s.discount_type ?? null,
    discountValue: s.discount_value != null ? Number(s.discount_value) : null,
    discountMinPeople: s.discount_min_people ?? null,
    discountedPrice: s.discounted_price != null ? Number(s.discounted_price) : null,
  };
}

// ── Filtros de búsqueda ─────────────────────────────────────────────────
export interface SpaceFilters {
  city?: string;
  type?: SpaceType;
  min_price?: number;
  max_price?: number;
  on_offer?: boolean;
  lat?: number;
  lng?: number;
  radius_km?: number;
  page?: number;
  page_size?: number;
}

export async function fetchSpaces(filters: SpaceFilters = {}): Promise<Space[]> {
  const json = await apiRequest("/spaces", { query: filters as Record<string, any> });
  const data = (json?.data ?? []) as ApiSpace[];
  return data.map(mapSpace);
}

export async function fetchSpace(id: string): Promise<Space> {
  const data = await apiRequest<ApiSpace>(`/spaces/${id}`);
  return mapSpace(data);
}

export async function fetchSimilarSpaces(id: string): Promise<Space[]> {
  try {
    const data = await apiRequest<ApiSpace[]>(`/spaces/${id}/similar`);
    return (data || []).map(mapSpace);
  } catch {
    return [];
  }
}

export async function fetchMySpaces(): Promise<Space[]> {
  const data = await apiRequest<ApiSpace[]>("/spaces/mine");
  return (data || []).map(mapSpace);
}

export interface AvailabilitySlot {
  start: string;
  end: string;
  available: boolean;
}

export async function fetchAvailability(id: string, date: string): Promise<AvailabilitySlot[]> {
  try {
    const data = await apiRequest<AvailabilitySlot[]>(`/spaces/${id}/availability`, { query: { date } });
    return data || [];
  } catch {
    return [];
  }
}

// SC-001 — actualizar oferta/descuento de un espacio (provider dueño)
export interface OfferUpdate {
  discount_active: boolean;
  discount_type: DiscountType | null;
  discount_value: number | null;
  discount_min_people: number | null;
}

export async function updateSpaceOffer(id: string, payload: OfferUpdate): Promise<Space> {
  const data = await apiRequest<ApiSpace>(`/spaces/${id}`, { method: "PATCH", body: payload });
  return mapSpace(data);
}

export interface SpaceUpdatePayload {
  name?: string;
  type?: SpaceType;
  description?: string;
  address?: string;
  city?: string;
  price_per_hour?: number;
  capacity?: number;
  amenities?: string[];
  is_active?: boolean;
}

export async function updateSpace(id: string, payload: SpaceUpdatePayload): Promise<Space> {
  const data = await apiRequest<ApiSpace>(`/spaces/${id}`, { method: "PATCH", body: payload });
  return mapSpace(data);
}

export async function fetchIncomingReservations(status?: string): Promise<IncomingReservation[]> {
  const query: Record<string, string> = {};
  if (status) query.status = status;
  const json = await apiRequest("/reservations/incoming", { query });
  return (json?.data ?? []) as IncomingReservation[];
}

export interface IncomingReservation {
  id: string;
  space_id: string;
  space_name: string | null;
  client_id: string;
  client_name: string | null;
  client_email: string | null;
  date: string;
  start_time: string;
  end_time: string;
  hours: number;
  num_people: number;
  subtotal: number;
  service_fee: number;
  total: number;
  status: string;
}

export interface SpaceCreatePayload {
  name: string;
  type: SpaceType;
  description?: string;
  address: string;
  city: string;
  price_per_hour: number;
  capacity: number;
  amenities: string[];
}

export async function createSpace(payload: SpaceCreatePayload): Promise<Space> {
  const data = await apiRequest<ApiSpace>("/spaces", { method: "POST", body: payload });
  return mapSpace(data);
}

export const TIME_SLOTS = [
  "08:00", "09:00", "10:00", "11:00", "12:00", "13:00",
  "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00",
];

export const formatCLP = (n: number) =>
  new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(n);
