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

Levanta 6 servicios: `api`, `db`, `redis`, `minio`, `worker`, `beat`.

### 4. Migrar base de datos

```bash
docker compose exec api alembic upgrade head
```

### 5. Verificar

```bash
curl http://localhost:8000/health
# {"status":"healthy","checks":{"db":"ok","redis":"ok"}}
```

---

## Documentación interactiva

Abre en el browser:

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI — prueba todos los endpoints |
| `http://localhost:8000/redoc` | ReDoc — documentación legible |
| `http://localhost:8000/openapi.json` | Schema OpenAPI (importar a Postman) |

### Importar a Postman

1. Postman → **Import** → **Link**
2. Pegar: `http://localhost:8000/openapi.json`
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
| `GET` | `/api/v1/spaces` | Listar espacios (filtros: ciudad, tipo, precio) |
| `POST` | `/api/v1/spaces` | Crear espacio (requiere rol provider) |
| `GET` | `/api/v1/spaces/{id}` | Detalle de espacio |
| `PATCH` | `/api/v1/spaces/{id}` | Editar espacio |
| `DELETE` | `/api/v1/spaces/{id}` | Eliminar espacio |
| `GET/PUT` | `/api/v1/spaces/{id}/schedules` | Horarios del espacio |
| `GET` | `/api/v1/spaces/{id}/availability` | Slots disponibles por fecha |
| `POST` | `/api/v1/reservations` | Crear reserva |
| `GET` | `/api/v1/reservations` | Mis reservas |
| `GET` | `/api/v1/reservations/{id}` | Detalle de reserva |
| `POST` | `/api/v1/reservations/{id}/cancel` | Cancelar reserva |
| `POST` | `/api/v1/payments/initiate` | Iniciar pago Transbank |
| `POST` | `/api/v1/payments/confirm` | Confirmar pago (webhook) |
| `GET` | `/api/v1/payments/{id}` | Estado de pago |

---

## Flujo de prueba básico (Swagger UI)

1. **Registrar usuario:** `POST /api/v1/auth/register`
2. **Login:** `POST /api/v1/auth/login` → copiar `access_token`
3. Click **Authorize** (candado arriba a la derecha) → pegar `Bearer <token>`
4. **Crear espacio:** `POST /api/v1/spaces`
5. **Ver disponibilidad:** `GET /api/v1/spaces/{id}/availability?date=2026-05-15`
6. **Reservar:** `POST /api/v1/reservations`

---

## Arquitectura

```
nginx :80
  └── api (FastAPI) :8000
        ├── PostgreSQL :5432   — datos principales
        ├── Redis :6379        — JWT blacklist + caché
        ├── MinIO :9000        — almacenamiento de imágenes
        ├── Celery Worker      — tareas asíncronas
        └── Celery Beat        — tareas periódicas (expiración reservas)
```

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
