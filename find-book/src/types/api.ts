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

export interface SpaceHost {
  name: string;
  bio?: string;
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
  discount_type?: string;
  discount_value?: number;
  discount_active?: boolean;
  discount_min_people?: number;
  discounted_price?: number;
  host?: SpaceHost;
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
  discount_active?: boolean;
  discount_type?: string;
  discount_value?: number;
  discount_min_people?: number;
  discounted_price?: number;
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
  redirect_url: string;
  token: string;
  provider: string;
}

// --- Reviews ---

export interface Review {
  id: string;
  reservation_id: string;
  space_id: string;
  rating: number;
  comment?: string;
  client_name: string;
  created_at: string;
}

export interface ReviewCreate {
  rating: number;
  comment?: string;
}

// --- Admin ---

export interface DailyReservation {
  date: string;
  reservations: number;
}

export interface AdminStats {
  total_spaces: number;
  active_spaces: number;
  total_users: number;
  total_reservations: number;
  total_revenue: number;
  revenue_30d: number;
  pending_disputes: number;
  daily_reservations: DailyReservation[];
}

export interface SystemConfig {
  platform_fee_percent: number;
  dispute_window_days: number;
  pending_reservation_ttl_minutes: number;
  maintenance_mode: boolean;
}

export interface HealthMetrics {
  cpu_percent?: number;
  memory_used_mb?: number;
  memory_total_mb?: number;
  memory_percent?: number;
  disk_used_gb?: number;
  disk_total_gb?: number;
  disk_percent?: number;
}

export interface HealthStatus {
  status: "healthy" | "degraded";
  checks: Record<string, "ok" | "fail">;
  metrics?: HealthMetrics;
}

export type SpaceApprovalStatus = "pending" | "approved" | "rejected";

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
  approval_status?: SpaceApprovalStatus;
  approval_note?: string | null;
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
  is_active: boolean;
  phone?: string;
  created_at: string;
}

export interface AdminReservationItem {
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
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string;
}

export type DisputeStatus = "open" | "under_review" | "resolved_refund" | "resolved_rejected";

export interface DisputeEvidence {
  id: string;
  url: string;
  filename: string | null;
  uploaded_at: string;
}

export interface DisputeItem {
  id: string;
  reservation_id: string;
  opened_by: string;
  opener_name: string | null;
  opener_email: string | null;
  space_name: string | null;
  reason: string;
  status: DisputeStatus;
  admin_notes: string | null;
  refund_amount: number | null;
  resolved_at: string | null;
  resolved_by: string | null;
  evidence: DisputeEvidence[];
  created_at: string;
}

export interface UserNote {
  id: string;
  body: string;
  admin_id: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  action: string;
  target_type: string | null;
  target_id: string | null;
  detail: Record<string, unknown> | null;
  admin_id: string | null;
  admin_name: string | null;
  created_at: string;
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
