import pytz
from enum import StrEnum

CHILE_TZ = pytz.timezone("America/Santiago")


class UserRole(StrEnum):
    CLIENT = "client"
    PROVIDER = "provider"
    ADMIN = "admin"


class ReservationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PaymentStatus(StrEnum):
    INITIATED = "initiated"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentProvider(StrEnum):
    STRIPE = "stripe"
    TRANSBANK = "transbank"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class SpaceType(StrEnum):
    OFICINA = "Oficina"
    CANCHA = "Cancha"
    SALA = "Sala"
    SALON = "Salón"
    ESTUDIO = "Estudio"
    TERRAZA = "Terraza"


class CancellationPolicy(StrEnum):
    FLEXIBLE = "flexible"
    MODERATE = "moderate"
    STRICT = "strict"


PENDING_RESERVATION_TTL_MINUTES = 15
GEO_CACHE_TTL_DAYS = 30
AVAILABILITY_CACHE_TTL_SECONDS = 60
