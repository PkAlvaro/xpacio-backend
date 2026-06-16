import uuid
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.database import get_session
from app.dependencies import get_redis, get_current_user, require_role
from app.constants import UserRole
from app.schemas.space import (
    SpaceCreate, SpaceUpdate, SpaceResponse, SpaceListItem,
    SpaceFilters, ScheduleCreate, SpaceScheduleOut, SubSpaceItem, SpaceImageOut,
)
from app.exceptions import DomainException
from app.services import space_service

router = APIRouter(prefix="/api/v1/spaces", tags=["spaces"])


@router.get(
    "",
    response_model=dict,
    summary="Listar espacios",
    description="""
Retorna la lista de espacios disponibles con filtros opcionales.

**Filtros disponibles:**
- `city`: filtrar por ciudad (ej. `Santiago`)
- `type`: tipo de espacio (`Oficina`, `Cancha`, `Sala`, `Salón`, `Estudio`, `Terraza`)
- `min_price` / `max_price`: rango de precio por hora en CLP
- `lat` + `lng` + `radius_km`: filtrar por cercanía geográfica (requiere los tres)
- `page` / `page_size`: paginación

**No requiere autenticación.**
""",
)
async def list_spaces(
    lat: float | None = Query(default=None, description="Latitud del punto de referencia"),
    lng: float | None = Query(default=None, description="Longitud del punto de referencia"),
    radius_km: float = Query(default=10.0, description="Radio de búsqueda en kilómetros"),
    type: str | None = Query(default=None, description="Tipo: Oficina | Cancha | Sala | Salón | Estudio | Terraza"),
    city: str | None = Query(default=None, description="Ciudad (ej. Santiago)"),
    min_price: int | None = Query(default=None, description="Precio mínimo por hora (CLP)"),
    max_price: int | None = Query(default=None, description="Precio máximo por hora (CLP)"),
    q: str | None = Query(default=None, description="Filtrar por nombre (ILIKE)"),
    on_offer: bool = Query(default=False, description="Solo espacios en oferta (descuento activo)"),
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=50, description="Resultados por página (máx 50)"),
    session: AsyncSession = Depends(get_session),
):
    from app.constants import SpaceType
    filters = SpaceFilters(
        lat=lat, lng=lng, radius_km=radius_km,
        type=SpaceType(type) if type else None,
        city=city, name=q, min_price=min_price, max_price=max_price,
        on_offer=on_offer,
        page=page, page_size=page_size,
    )
    items, total = await space_service.list_spaces(filters, session)
    return {
        "success": True,
        "data": [i.model_dump() for i in items],
        "meta": {"total": total, "page": page, "page_size": page_size},
    }


@router.post(
    "",
    response_model=dict,
    status_code=201,
    summary="Crear espacio",
    description="""
Crea un nuevo espacio de arriendo. Solo usuarios con rol `provider` o `admin` pueden crear espacios.

Si el usuario no tiene perfil de proveedor aún, se crea automáticamente.

El sistema geocodifica automáticamente la dirección usando OpenStreetMap (Nominatim)
para obtener las coordenadas `lat` y `lng`.

Después de crear el espacio, configurar sus horarios con `PUT /spaces/{id}/schedules`.

**Requiere autenticación con rol `provider` o `admin`.**
""",
)
async def create_space(
    data: SpaceCreate,
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.provider import Provider
    result = await session.execute(select(Provider).where(Provider.user_id == user.id))
    provider = result.scalar_one_or_none()
    if not provider:
        provider = Provider(id=_uuid.uuid4(), user_id=user.id)
        session.add(provider)
        await session.flush()

    space = await space_service.create_space(data, provider.id, session, redis)
    return {"success": True, "data": SpaceResponse.from_orm_with_amenities(space).model_dump()}


@router.get(
    "/suggest",
    response_model=dict,
    summary="Sugerencias fuzzy por nombre",
)
async def suggest_spaces(
    q: str = Query(default="", min_length=1, description="Texto a buscar en el nombre del espacio"),
    limit: int = Query(default=8, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
):
    items = await space_service.suggest_spaces(q, session, limit)
    return {"success": True, "data": items}


@router.get(
    "/mine",
    response_model=dict,
    summary="Mis espacios",
    description="""
Retorna todos los espacios del proveedor autenticado, incluyendo los inactivos.

**Requiere autenticación con rol `provider` o `admin`.**
""",
)
async def my_spaces(
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    spaces = await space_service.list_provider_spaces(user.id, session)
    return {"success": True, "data": [SpaceResponse.from_orm_with_amenities(s).model_dump() for s in spaces]}


@router.get(
    "/{space_id_or_slug}",
    response_model=dict,
    summary="Ver detalle de un espacio",
    description="""
Retorna el detalle completo de un espacio. Acepta UUID o slug (ej. `gam-centro-gabriela-mistral-santiago`).

**No requiere autenticación.**
""",
)
async def get_space(space_id_or_slug: str, session: AsyncSession = Depends(get_session)):
    space = await space_service.resolve_space(space_id_or_slug, session)
    return {"success": True, "data": SpaceResponse.from_orm_with_amenities(space).model_dump()}


@router.get(
    "/{space_id}/similar",
    response_model=dict,
    summary="Espacios similares recomendados (SC-002)",
    description="""
Retorna un mínimo de 3 espacios similares al indicado, comparando por **tipo**,
**ciudad** o **rango de precio ±30%**, excluyendo el propio espacio.

Si no existen suficientes espacios similares en el catálogo piloto, se completa de
forma controlada con los espacios mejor calificados (fallback sin error, nunca vacío
si hay al menos otros espacios activos).

**No requiere autenticación.**
""",
)
async def get_similar_spaces(
    space_id: uuid.UUID,
    limit: int = Query(default=6, ge=3, le=12, description="Máximo de espacios a retornar"),
    session: AsyncSession = Depends(get_session),
):
    items = await space_service.get_similar_spaces(space_id, session, limit)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.patch(
    "/{space_id}",
    response_model=dict,
    summary="Editar espacio",
    description="""
Actualiza parcialmente un espacio existente. Solo se modifican los campos enviados.

Solo el proveedor dueño del espacio (o admin) puede editarlo.

Para desactivar un espacio temporalmente: `{ "is_active": false }`

**Requiere autenticación con rol `provider` o `admin`.**
""",
)
async def update_space(
    space_id: uuid.UUID,
    data: SpaceUpdate,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    space = await space_service.update_space(space_id, data, user.id, session)
    return {"success": True, "data": SpaceResponse.from_orm_with_amenities(space).model_dump()}


@router.delete(
    "/{space_id}",
    status_code=204,
    summary="Eliminar (desactivar) espacio",
    description="""
Desactiva un espacio (no lo elimina físicamente de la base de datos).

Un espacio desactivado (`is_active = false`) no aparece en búsquedas
y no acepta nuevas reservas.

Solo el proveedor dueño del espacio (o admin) puede desactivarlo.

**Requiere autenticación con rol `provider` o `admin`.**
""",
)
async def delete_space(
    space_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    await space_service.delete_space(space_id, user.id, session)


@router.put(
    "/{space_id}/schedules",
    response_model=dict,
    summary="Configurar horarios del espacio",
    description="""
Define los horarios de disponibilidad semanal del espacio. Reemplaza completamente
los horarios anteriores.

Enviar un array con uno o más días de la semana:
- `day_of_week`: 0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo
- `open_time`: hora de apertura (HH:MM)
- `close_time`: hora de cierre (HH:MM)

Ejemplo: configurar Lunes a Viernes de 08:00 a 20:00:
```json
[
  {"day_of_week": 0, "open_time": "08:00", "close_time": "20:00"},
  {"day_of_week": 1, "open_time": "08:00", "close_time": "20:00"},
  {"day_of_week": 2, "open_time": "08:00", "close_time": "20:00"},
  {"day_of_week": 3, "open_time": "08:00", "close_time": "20:00"},
  {"day_of_week": 4, "open_time": "08:00", "close_time": "20:00"}
]
```

**Requiere autenticación con rol `provider` o `admin`.**
""",
)
async def set_schedules(
    space_id: uuid.UUID,
    schedules: list[ScheduleCreate],
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    result = await space_service.set_schedules(space_id, schedules, user.id, session)
    return {"success": True, "data": [SpaceScheduleOut.model_validate(s).model_dump() for s in result]}


@router.post(
    "/{space_id}/images",
    response_model=dict,
    summary="Subir imagen (proveedor dueño)",
)
async def upload_image(
    space_id: uuid.UUID,
    file: UploadFile = File(...),
    set_primary: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise DomainException("Solo se permiten archivos de imagen")
    space = await space_service.get_space(space_id, session)
    await space_service._assert_owner(space, user.id, session)
    img = await space_service.upload_space_image(space_id, file, session, set_primary)
    return {"success": True, "data": SpaceImageOut.model_validate(img).model_dump()}


@router.delete(
    "/{space_id}/images/{image_id}",
    status_code=204,
    summary="Eliminar imagen (proveedor dueño)",
)
async def delete_image(
    space_id: uuid.UUID,
    image_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    space = await space_service.get_space(space_id, session)
    await space_service._assert_owner(space, user.id, session)
    await space_service.delete_space_image(space_id, image_id, session)


@router.patch(
    "/{space_id}/images/{image_id}/primary",
    response_model=dict,
    summary="Marcar imagen como principal (proveedor dueño)",
)
async def set_primary_image(
    space_id: uuid.UUID,
    image_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    space = await space_service.get_space(space_id, session)
    await space_service._assert_owner(space, user.id, session)
    await space_service.set_primary_image(space_id, image_id, session)
    return {"success": True}


@router.get(
    "/{space_id}/sub-spaces",
    response_model=dict,
    summary="Sub-espacios / salas de un espacio",
    description="""
Retorna las salas o sub-espacios disponibles dentro de un espacio padre (venue).

Ejemplo: un centro cultural puede tener Sala A, Sala B y Terraza como sub-espacios
que se pueden reservar independientemente.

**No requiere autenticación.**
""",
)
async def get_sub_spaces(space_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    items = await space_service.list_sub_spaces(space_id, session)
    return {"success": True, "data": [SubSpaceItem.model_validate(s).model_dump() for s in items]}


@router.get(
    "/{space_id}/schedules",
    response_model=dict,
    summary="Ver horarios del espacio",
    description="""
Retorna los horarios de disponibilidad configurados para el espacio.

**No requiere autenticación.**
""",
)
async def get_schedules(space_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    space = await space_service.get_space(space_id, session)
    return {"success": True, "data": [SpaceScheduleOut.model_validate(s).model_dump() for s in space.schedules]}
