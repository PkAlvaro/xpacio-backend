# Xpacio Backend

API REST para reserva de espacios bajo demanda.  
**Stack:** FastAPI · PostgreSQL 15 · Redis 7 · Celery · Transbank WebpayPlus · Docker Compose

---

## Requisitos

- Docker Desktop (o Docker Engine + Compose plugin)
- Git

---

## Setup rápido

### 1. Clonar

```bash
git clone https://github.com/PkAlvaro/xpacio-backend.git
cd xpacio-backend
```

### 2. Variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus valores. Las variables mínimas para desarrollo local ya tienen defaults funcionales en `.env.example`.

> **Transbank:** en modo prototipo/desarrollo usa las credenciales de integración que vienen por defecto — no requiere cuenta real.

### 3. Levantar servicios

```bash
docker compose up --build -d
```

Levanta 8 servicios: `frontend`, `nginx`, `api`, `db`, `redis`, `minio`, `worker`, `beat`.

### 4. Migrar base de datos

```bash
docker compose exec api alembic upgrade head
```

### 5. Verificar

```bash
curl http://localhost/health
# {"status":"healthy","checks":{"db":"ok","redis":"ok"}}
```

| URL | Descripción |
|-----|-------------|
| `http://localhost/` | Frontend React |
| `http://localhost/api/v1/...` | Backend API |
| `http://localhost/docs` | Swagger UI |

---

## Documentación interactiva

Abre en el browser:

| URL | Descripción |
|-----|-------------|
| `http://localhost/docs` | Swagger UI — prueba todos los endpoints |
| `http://localhost/redoc` | ReDoc — documentación legible |
| `http://localhost/openapi.json` | Schema OpenAPI (importar a Postman) |

### Importar a Postman

1. Postman → **Import** → **Link**
2. Pegar: `http://localhost/openapi.json`
3. Genera la colección completa automáticamente

---

## Endpoints disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio |
| `POST` | `/api/v1/auth/register` | Registro de usuario |
| `POST` | `/api/v1/auth/login` | Login → access + refresh token |
| `POST` | `/api/v1/auth/refresh` | Renovar access token |
| `POST` | `/api/v1/auth/logout` | Invalidar tokens |
| `GET` | `/api/v1/auth/me` | Perfil del usuario autenticado |
| `GET` | `/api/v1/spaces` | Listar espacios (filtros: ciudad, tipo, precio, ubicación) |
| `POST` | `/api/v1/spaces` | Crear espacio (requiere rol `provider` o `admin`) |
| `GET` | `/api/v1/spaces/{id}` | Detalle de espacio |
| `PATCH` | `/api/v1/spaces/{id}` | Editar espacio (solo dueño o admin) |
| `DELETE` | `/api/v1/spaces/{id}` | Desactivar espacio (solo dueño o admin) |
| `PUT` | `/api/v1/spaces/{id}/schedules` | Configurar horarios semanales |
| `GET` | `/api/v1/spaces/{id}/schedules` | Ver horarios configurados |
| `GET` | `/api/v1/spaces/{id}/availability` | Slots disponibles por fecha |
| `POST` | `/api/v1/reservations` | Crear reserva |
| `GET` | `/api/v1/reservations` | Mis reservas (filtro por estado) |
| `GET` | `/api/v1/reservations/{id}` | Detalle de reserva |
| `POST` | `/api/v1/reservations/{id}/cancel` | Cancelar reserva |
| `POST` | `/api/v1/payments/initiate` | Iniciar pago Transbank |
| `POST` | `/api/v1/payments/confirm` | Confirmar pago (webhook Transbank) |
| `GET` | `/api/v1/payments/{id}` | Estado de pago |
| `PATCH` | `/api/v1/admin/users/{id}/role` | Cambiar rol de usuario (solo admin) |

---

## Flujo de prueba completo (Swagger UI)

Abrir `http://localhost/docs`

### Flujo cliente → reserva → pago

1. **Registrar usuario:** `POST /api/v1/auth/register`
   ```json
   { "name": "Test User", "email": "test@test.com", "password": "seguro123" }
   ```
2. **Login:** `POST /api/v1/auth/login` → copiar `access_token`
3. Click **Authorize** (candado arriba a la derecha) → pegar `Bearer <token>`
4. **Ver espacios disponibles:** `GET /api/v1/spaces`
5. **Ver disponibilidad:** `GET /api/v1/spaces/{id}/availability?date=2026-05-20`
6. **Reservar:** `POST /api/v1/reservations`
7. **Iniciar pago:** `POST /api/v1/payments/initiate` → obtener `webpay_url`
8. Visitar `webpay_url` → usar credenciales de integración Transbank (ver abajo)

### Flujo admin → crear espacio

1. El primer admin debe crearse directo en BD:
   ```sql
   UPDATE users SET role='admin' WHERE email='tu@email.com';
   ```
2. **Login** con cuenta admin → **Authorize**
3. **Promover usuario a provider:** `PATCH /api/v1/admin/users/{user_id}/role`
   ```json
   { "role": "provider" }
   ```
4. **Login** con cuenta provider → **Authorize**
5. **Crear espacio:** `POST /api/v1/spaces` (el perfil de proveedor se crea automáticamente)
6. **Configurar horarios:** `PUT /api/v1/spaces/{id}/schedules`

### Credenciales Transbank (ambiente integración)

| Campo | Valor |
|-------|-------|
| Número de tarjeta | `4051 8856 0044 6623` |
| CVV | `123` |
| RUT | `11.111.111-1` |
| Clave | `123` |

---

## Diagramas de Arquitectura

### 1. Arquitectura Global del Sistema

```
                       ┌─────────────────────────────────────┐
                       │  Browser (React Frontend)           │
                       └──────────────┬──────────────────────┘
                                      │ HTTPS
                       ┌──────────────▼──────────────────────┐
                       │ Docker Compose Environment           │
                       │                                      │
                       │  ┌─────────────────────────────────┐ │
                       │  │  Nginx Reverse Proxy (:80/:443) │ │
                       │  └────────────────┬────────────────┘ │
                       │                   │                   │
        ┌──────────────┼───────────────────┼───────────────┐   │
        │              │                   │               │   │
    ┌───▼───┐    ┌─────▼─────┐      ┌─────▼────┐    ┌────▼─┐  │
    │FastAPI│    │PostgreSQL │      │  Redis   │    │MinIO │  │
    │ :8000 │    │   :5432   │      │  :6379   │    │:9000 │  │
    └───┬───┘    └───────────┘      └──────────┘    └──────┘  │
        │                                                       │
    ┌───▼──────────────┐                                        │
    │  Celery Worker   │  ← tareas asíncronas                  │
    │  Celery Beat     │  ← scheduler (cada 5 min)             │
    └──────────────────┘                                        │
                       └──────────────────────────────────────┘
                       ┌──────────────────────────────────────┐
                       │  Servicios Externos                  │
                       │  • Nominatim (geocoding)             │
                       │  • Transbank WebpayPlus (pagos)      │
                       └──────────────────────────────────────┘
```

---

### 2. Arquitectura en Capas (FastAPI)

```
┌────────────────────────────────────────────────────────────────┐
│ HTTP Layer (Routers)                                           │
│   /auth  ·  /spaces  ·  /reservations  ·  /payments  ·/admin  │
└────────────────────────┬───────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────┐
│ Dependency Injection                                           │
│   get_db()  ·  get_current_user()  ·  require_role()          │
└────────────────────────┬───────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────┐
│ Service Layer (Business Logic)                                 │
│   AuthService  ·  SpaceService  ·  ReservationService         │
│   PaymentService  ·  GeocodingService  ·  AvailabilityService │
└────────────────────────┬───────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────┐
│ Data Access Layer                                              │
│   SQLAlchemy ORM Models  ·  Pydantic Schemas                  │
│   PostgreSQL (asyncpg)  ·  Redis                              │
└────────────────────────────────────────────────────────────────┘
```

---

### 3. Flujo de Autenticación

```
                    USUARIO
                       │
         ┌─────────────┼─────────────┐
         │             │             │
     [REGISTER]    [LOGIN]       [REFRESH]
         │             │             │
         │      ┌──────▼──────┐      │
         │      │ /auth/login │      │
         │      └──────┬──────┘      │
         │             │             │
    ┌────▼─────────────▼─────────────▼────┐
    │  PostgreSQL — users table            │
    │  • Hashear password (bcrypt)         │
    │  • Verificar credenciales            │
    └─────────────────┬────────────────────┘
                      │
    ┌─────────────────▼────────────────────┐
    │  Redis                               │
    │  SET jti_blacklist (logout)          │
    │  TTL = tiempo restante del token     │
    └─────────────────┬────────────────────┘
                      │
    ┌─────────────────▼────────────────────┐
    │  Respuesta al cliente                │
    │  • access_token  (JWT, 15 min)       │
    │  • refresh_token (JWT, 7 días)       │
    └──────────────────────────────────────┘
```

---

### 4. Flujo de Reserva y Pago

```
Paso 1 — CREAR RESERVA
  │
  ├─→ Verificar conflictos (mismo espacio + fecha + horario superpuesto)
  │     └─→ Constraint PostgreSQL: EXCLUDE USING gist (int4range WITH &&)
  ├─→ INSERT reservations (status = 'pending')
  └─→ Retorna reservation_id + total

Paso 2 — INICIAR PAGO
  │
  ├─→ POST /api/v1/payments/initiate
  ├─→ Transbank.Transaction.create(monto, return_url)
  └─→ Retorna webpay_url → redirigir al usuario

Paso 3 — USUARIO PAGA EN TRANSBANK
  │
  ├─→ Formulario de pago Transbank
  └─→ Webhook a POST /api/v1/payments/confirm?token_ws=...

Paso 4 — CONFIRMAR PAGO (Webhook)
  │
  ├─→ Transbank.Transaction.commit(token)
  ├─→ SI response_code == 0:
  │     ├─→ payments.status = 'paid'
  │     └─→ reservations.status = 'confirmed'
  └─→ SI falla:
        ├─→ payments.status = 'failed'
        └─→ reservations.status = 'cancelled'

Paso 5 — TRANSICIONES AUTOMÁTICAS (Celery Beat)
  │
  ├─→ pending sin pago > 15 min   → expired
  ├─→ confirmed + start_time <= now → active
  └─→ active + end_time <= now    → finished
```

---

### 5. Modelo de Datos (ERD)

```
users
├── id (UUID PK)
├── name, email (UNIQUE), password_hash
├── role: client | provider | admin
│
├──< providers (1:1)
│     └── bank_rut, verification_status
│
├──< spaces (1:N via provider_id)
│     ├── name, description, type, address, city
│     ├── lat, lng (geocodificado por Nominatim)
│     ├── price_per_hour, capacity, is_active
│     │
│     ├──< space_schedules (horarios semanales)
│     │     └── day_of_week, open_time, close_time, slot_minutes
│     │
│     ├──< space_images
│     └──< space_amenities
│
└──< reservations (1:N via client_id)
      ├── space_id (FK)
      ├── date, start_time, end_time
      ├── total, status: pending|confirmed|active|finished|cancelled|expired
      │
      └──< payments (1:1)
            ├── token (Transbank), buy_order
            ├── amount, status: pending|paid|failed|refunded
            └── raw_response (JSONB)
```

---

### 6. Estructura del Proyecto

```
xpacio-backend/
├── docker-compose.yml           # Producción (6 servicios)
├── docker-compose.override.yml  # Dev: hot-reload, puertos expuestos
├── Dockerfile
├── nginx/
│   └── nginx.conf               # Reverse proxy
├── alembic/
│   └── versions/
│       └── 0001_initial_schema.py
│
└── app/
    ├── main.py                  # FastAPI app + lifespan + CORS
    ├── config.py                # Pydantic Settings (env vars)
    ├── database.py              # SQLAlchemy async engine
    ├── dependencies.py          # get_db, get_current_user, require_role
    ├── constants.py             # Enums: UserRole, ReservationStatus…
    ├── exceptions.py            # DomainException + handlers
    │
    ├── models/                  # SQLAlchemy ORM
    │   ├── user.py
    │   ├── space.py
    │   ├── reservation.py
    │   └── payment.py
    │
    ├── schemas/                 # Pydantic (request/response)
    │   ├── auth.py
    │   ├── space.py
    │   ├── reservation.py
    │   └── payment.py
    │
    ├── routers/                 # Endpoints HTTP
    │   ├── auth.py
    │   ├── spaces.py
    │   ├── reservations.py
    │   ├── payments.py
    │   └── admin.py             # Gestión de roles (solo admin)
    │
    ├── services/                # Lógica de negocio
    │   ├── auth_service.py
    │   ├── space_service.py
    │   ├── availability_service.py
    │   ├── reservation_service.py
    │   ├── payment_service.py
    │   ├── geocoding_service.py
    │   └── redis_service.py
    │
    ├── utils/
    │   └── time_utils.py        # Timezone Chile (America/Santiago)
    │
    └── workers/
        ├── celery_app.py
        ├── beat_schedule.py
        └── tasks/
            ├── reservation_tasks.py
            └── payment_tasks.py
```

---

### 7. Integraciones Externas

| Servicio | Propósito | Detalles |
|----------|-----------|----------|
| **Nominatim** | Geocoding | Cache Redis 30 días, límite 1 req/seg |
| **Transbank** | Pagos | WebpayPlus SDK, env `integration` gratis |
| **PostgreSQL** | Datos principales | Driver async `asyncpg` |
| **Redis** | Caché + JWT blacklist | TTL por tipo de dato |
| **MinIO** | Imágenes de espacios | Compatible S3 |
| **Celery** | Tareas background | Expiración reservas, transiciones |

---

## Comandos útiles

```bash
# Ver logs de la API
docker compose logs api -f

# Ver logs de todos los servicios
docker compose logs -f

# Detener todo
docker compose down

# Detener y borrar volúmenes (reset DB)
docker compose down -v

# Acceder a la DB directamente
docker compose exec db psql -U xpacio -d xpacio

# Ejecutar migraciones
docker compose exec api alembic upgrade head

# Ver historial de migraciones
docker compose exec api alembic history
```

---

## Variables de entorno principales

Ver `.env.example` para la lista completa. Las más relevantes:

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Conexión PostgreSQL async |
| `REDIS_URL` | Conexión Redis |
| `SECRET_KEY` | Clave JWT (cambiar en producción) |
| `TRANSBANK_COMMERCE_CODE` | Código de comercio Transbank |
| `TRANSBANK_API_KEY` | API key Transbank |
| `TRANSBANK_ENV` | `integration` o `production` |
| `FRONTEND_URL` | URL del frontend (CORS) |
