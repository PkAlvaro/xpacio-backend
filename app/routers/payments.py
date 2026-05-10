import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.schemas.payment import PaymentInitiate, PaymentResponse
from app.services import payment_service
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post(
    "/initiate",
    response_model=dict,
    status_code=201,
    summary="Iniciar pago con Transbank",
    description="""
Inicia el proceso de pago para una reserva existente en estado `pending`.

El sistema genera una transacción en Transbank WebpayPlus y retorna:
- `webpay_url`: URL a la que se debe redirigir al usuario para que ingrese sus datos de pago
- `token`: token de la transacción (lo usa Transbank internamente)
- `payment_id`: ID del pago creado en el sistema

**Flujo completo:**
1. Crear reserva → `POST /reservations`
2. Iniciar pago → `POST /payments/initiate` → obtener `webpay_url`
3. Redirigir al usuario a `webpay_url`
4. Transbank redirige al usuario de vuelta y llama al webhook → `POST /payments/confirm`

**Ambiente de integración (pruebas):**
- Número de tarjeta: `4051 8856 0044 6623`
- CVV: `123`
- RUT: `11.111.111-1`
- Clave: `123`

**Requiere autenticación.**
""",
)
async def initiate_payment(
    data: PaymentInitiate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    payment = await payment_service.initiate_payment(data.reservation_id, user.id, session)
    return {
        "success": True,
        "data": {
            "payment_id": str(payment.id),
            "webpay_url": payment._webpay_url,
            "token": payment.token,
        },
    }


@router.post(
    "/confirm",
    response_model=dict,
    summary="Confirmar pago (webhook Transbank)",
    description="""
Endpoint de callback que Transbank llama automáticamente al completar el pago.

Recibe el `token_ws` como query parameter (lo envía Transbank en la redirección).
Confirma la transacción con Transbank y actualiza los estados:
- Si el pago fue exitoso: `payment.status = paid`, `reservation.status = confirmed`
- Si falló: `payment.status = failed`, `reservation.status = cancelled`

**Este endpoint NO requiere autenticación JWT** — es llamado directamente por Transbank.

Para pruebas manuales en Swagger: usar el `token` obtenido en `POST /payments/initiate`.
""",
)
async def confirm_payment(
    token_ws: str = Query(..., description="Token enviado por Transbank en la redirección de vuelta"),
    session: AsyncSession = Depends(get_session),
):
    payment = await payment_service.confirm_payment(token_ws, session)
    return {"success": True, "data": PaymentResponse.model_validate(payment).model_dump()}


@router.get(
    "/{payment_id}",
    response_model=dict,
    summary="Ver estado de un pago",
    description="""
Retorna el detalle y estado actual de un pago.

Estados posibles:
- `initiated`: pago creado, usuario aún no completó el formulario de Transbank
- `paid`: pago confirmado exitosamente
- `failed`: pago rechazado o error en Transbank
- `refunded`: pago reembolsado

Solo el dueño de la reserva asociada puede consultar el pago.

**Requiere autenticación.**
""",
)
async def get_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    payment = await payment_service.get_payment(payment_id, user.id, session)
    return {"success": True, "data": PaymentResponse.model_validate(payment).model_dump()}
