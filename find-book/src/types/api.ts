export type UserRole = "client" | "provider" | "admin";

export type SpaceType =
  | "Oficina"
  | "Cancha"
  | "Sala"
  | "Salón"
  | "Estudio"
  | "Terraza";

export type CancellationPolicy = "flexible" | "moderate" | "strict";

export type ReservationStatus =
  | "pending"
  | "confirmed"
  | "active"
  | "finished"
  | "cancelled"
  | "expired";

export type PaymentStatus = "initiated" | "paid" | "failed" | "refunded";

// --- Auth ---

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone?: string;
}

// --- Spaces ---

export interface SpaceImage {
  id: string;
  url: string;
  is_primary: boolean;
  display_order: number;
}

export interface SpaceSchedule {
  id: string;
  day_of_week: number;
  open_time: string;
  close_time: string;
}

export interface SpaceDetail {
  id: string;
  slug?: string;
  provider_id: string;
  name: string;
  type: SpaceType;
  description?: string;
  address: string;
  city: string;
  lat?: number;
  lng?: number;
  price_per_hour: number;
  capacity: number;
  cancellation_policy: CancellationPolicy;
  cancellation_hours: number;
  is_active: boolean;
  rating: number;
  review_count: number;
  images: SpaceImage[];
  schedules: SpaceSchedule[];
  amenities: string[];
}

export interface SubSpaceItem {
  id: string;
  slug?: string;
  name: string;
  type: SpaceType;
  description?: string;
  price_per_hour: number;
  capacity: number;
  rating: number;
  is_active: boolean;
  primary_image?: string;
  amenities: string[];
  discount_active: boolean;
  discounted_price?: number;
}

export interface SpaceListItem {
  id: string;
  slug?: string;
  name: string;
  type: SpaceType;
  city: string;
  address: string;
  lat?: number;
  lng?: number;
  price_per_hour: number;
  capacity: number;
  rating: number;
  review_count: number;
  is_active: boolean;
  primary_image?: string;
  distance_km?: number;
}

export interface SpaceFilters {
  lat?: number;
  lng?: number;
  radius_km?: number;
  type?: SpaceType;
  city?: string;
  q?: string;
  min_price?: number;
  max_price?: number;
  page?: number;
  page_size?: number;
}

// --- Availability ---

export interface TimeSlot {
  start: string;
  end: string;
  available: boolean;
}

// --- Reservations ---

export interface Reservation {
  id: string;
  space_id: string;
  client_id: string;
  date: string;
  start_time: string;
  end_time: string;
  hours: number;
  subtotal: number;
  service_fee: number;
  total: number;
  status: ReservationStatus;
}

// --- Payments ---

export interface Payment {
  id: string;
  reservation_id: string;
  amount: number;
  status: PaymentStatus;
  authorized_at?: string;
}

export interface PaymentInitiateResponse {
  payment_id: string;
  webpay_url: string;
  token: string;
}

// --- Admin ---

export interface AdminStats {
  total_spaces: number;
  active_spaces: number;
  total_users: number;
  total_reservations: number;
}

export interface AdminSpaceListItem {
  id: string;
  slug?: string;
  name: string;
  type: SpaceType;
  city: string;
  address: string;
  price_per_hour: number;
  capacity: number;
  is_active: boolean;
  rating: number;
  review_count: number;
  parent_id?: string;
  primary_image?: string;
  provider_name?: string;
  created_at: string;
}

export interface AdminSpaceCreate {
  name: string;
  type: SpaceType;
  description?: string;
  address: string;
  city: string;
  price_per_hour: number;
  capacity: number;
  cancellation_policy?: string;
  cancellation_hours?: number;
  amenities?: string[];
  parent_id?: string;
}

export interface AdminSpaceUpdate {
  name?: string;
  slug?: string;
  type?: SpaceType;
  description?: string;
  address?: string;
  city?: string;
  price_per_hour?: number;
  capacity?: number;
  cancellation_policy?: string;
  cancellation_hours?: number;
  is_active?: boolean;
  amenities?: string[];
  discount_active?: boolean;
  discount_type?: string;
  discount_value?: number;
  discount_min_people?: number;
}

export interface AdminUserListItem {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone?: string;
}

// --- API envelope ---

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  meta?: {
    total: number;
    page: number;
    page_size: number;
  };
}
