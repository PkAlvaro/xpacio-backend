# Xpacio — Integración Frontend + Backend

Guía para levantar Xpacio (FastAPI + Postgres + Redis + frontend React) completamente en
local con un solo comando, e integrar pagos (Transbank/Stripe), geolocalización (Google Maps)
y las solicitudes de cambio **SC-001 (Descuentos/Ofertas)** y **SC-002 (Espacios similares)**.

---

## 1. Cómo levantar todo

Desde la carpeta `xpacio-backend/`:

```bash
docker compose up --build
```

Esto construye y levanta: **db** (Postgres), **redis**, **api** (FastAPI), **worker** y **beat**
(Celery), **minio**, **frontend** (build estático de `find-book`) y **nginx**.

Al iniciar, el contenedor `api`:
1. corre las migraciones Alembic (`alembic upgrade head`),
2. siembra datos demo idempotentes (`python -m app.seed`),
3. arranca uvicorn.

Cuando todos los healthchecks estén verdes, abre:

| URL | Qué es |
|-----|--------|
| **http://localhost** | Frontend (la app) |
| http://localhost/docs | Swagger del backend |
| http://localhost/health | Healthcheck |

> El frontend se sirve en `/` y nginx hace `proxy_pass` de `/api/` hacia `api:8000`,
> por lo que **todo es mismo-origen** (sin problemas de CORS).

### Usuarios y datos demo

El seed crea un **anfitrión demo** y 7 espacios en Santiago (varios con ofertas activas):

- **Email:** `anfitrion@xpacio.cl`
- **Password:** `xpacio1234`

Puedes registrar tus propios usuarios desde `/registro` (eligiendo *Arrendatario* o *Anfitrión*).

---

## 2. Variables de entorno que faltan configurar (opcionales)

La app **funciona end-to-end sin estas keys** (degradación elegante). Edítalas en
`xpacio-backend/.env` y reconstruye (`docker compose up --build`) si las quieres habilitar:

| Variable | Sin configurar (default) | Para habilitarla |
|----------|--------------------------|------------------|
| `GOOGLE_MAPS_API_KEY` | El backend geocodifica vía **OpenStreetMap/Nominatim** (gratis) y el frontend muestra un *fallback* con la lista de espacios en vez del mapa. | Pega tu API key (`AIza...`). Se inyecta también al build del frontend como `VITE_GOOGLE_MAPS_API_KEY` (build arg). |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | El pago Stripe no está operativo; el frontend avisa y sugiere usar Transbank. | Pega tus claves de prueba `sk_test_...` / `whsec_...`. |

**Transbank Webpay Plus** ya viene con **credenciales de integración** (no requieren cuenta real):
está operativo desde el primer `docker compose up`.

- Tarjeta de prueba: **VISA 4051 8856 0044 6623**, CVV **123**
- RUT **11.111.111-1**, clave **123**

---

## 3. Endpoints nuevos / modificados

### SC-001 — Descuentos / Ofertas (REQ-2.3, REQ-3.5)

Campos nuevos en `Space` (tabla `spaces`, migración `0004`): `discount_type`
(`percentage` | `volume`), `discount_value` (%), `discount_active` (bool),
`discount_min_people` (int). El precio base histórico **nunca** se altera.

- `GET /api/v1/spaces?on_offer=true` — filtra solo espacios con descuento activo.
- `PATCH /api/v1/spaces/{id}` — extendido para editar los campos de oferta (solo el
  proveedor dueño / admin).
- `GET /api/v1/spaces` y `GET /api/v1/spaces/{id}` — ahora devuelven los campos de
  descuento + `discounted_price` (precio/hora ya con descuento).
- **Cálculo server-side:** `space_service.calculate_price(space, hours, num_people)` aplica
  el descuento (porcentual, o por volumen si `num_people >= discount_min_people`).
  `reservation_service.create_reservation` lo usa para `subtotal`/`total`, de modo que el
  monto enviado a Transbank/Stripe ya incluye el descuento.
- `POST /api/v1/reservations` acepta `num_people` (para el descuento por volumen).

### SC-002 — Espacios similares (REQ-3.6)

- `GET /api/v1/spaces/{id}/similar` — retorna mínimo 3 espacios similares por **tipo**,
  **ciudad** o **precio ±30%**, excluyendo el propio. Si no hay suficientes, completa con
  los mejor calificados (fallback controlado, sin error ni lista vacía). Query indexada,
  ordenada por `rating DESC, review_count DESC`.

### Otros ajustes de integración

- `POST /api/v1/auth/register` — acepta `role` opcional (`client` | `provider`) para poder
  registrarse como anfitrión y publicar/gestionar espacios. `admin` no es auto-asignable.
- `GET|POST /api/v1/payments/transbank/return` — URL de retorno de Webpay; recibe el POST de
  Transbank y redirige (303) a la ruta SPA `/pago/retorno?token_ws=...` donde el frontend
  confirma con `POST /api/v1/payments/transbank/confirm`.
- CORS ampliado a los orígenes locales habituales.
- Geocoding con *fallback* a Nominatim cuando no hay API key real de Google.

---

## 4. Flujo end-to-end (resumen)

1. **Registro/Login** → `/auth/register`, `/auth/login` (tokens guardados en memoria +
   localStorage, refresco automático ante 401 vía `/auth/refresh`).
2. **Explorar** → Home y Buscar consumen `GET /spaces` (con filtros `city`, `max_price`,
   `on_offer`, etc.). Pestaña **Ofertas** y filtro **Solo en oferta**.
3. **Detalle** → `GET /spaces/{id}` + `GET /spaces/{id}/availability` (deshabilita horarios
   ocupados) + carrusel **Espacios Similares** (`/spaces/{id}/similar`) + mapa Google.
4. **Reservar** → `POST /reservations` (usa subtotal/total reales con descuento).
5. **Pagar** → selector Transbank/Stripe → `POST /payments/{provider}/initiate` → redirección
   a la pasarela → retorno y confirmación.
6. **Mis reservas** → `GET /reservations`, cancelar con `POST /reservations/{id}/cancel`.
7. **Anfitrión** → `/mis-espacios`: activa ofertas y descuentos (`PATCH /spaces/{id}`).

---

## 5. Notas

- Modo desarrollo: `docker-compose.override.yml` expone la API en `localhost:8001` con
  `--reload` y monta el código. El comando de la API corre migraciones + seed en ambos modos.
- Favoritos: se guardan en `localStorage` (no hay endpoint dedicado); las reservas viven en
  el backend.
- Frontend: `VITE_API_URL=/api/v1` y `VITE_GOOGLE_MAPS_API_KEY` se inyectan como build args.
