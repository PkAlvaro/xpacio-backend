// Compatibilidad: el catálogo ahora viene del backend (ver src/lib/spaces.ts).
// Este archivo solo re-exporta los tipos y helpers para no romper imports existentes.
export type { Space, SpaceType, DiscountType } from "@/lib/spaces";
export { formatCLP, TIME_SLOTS } from "@/lib/spaces";
