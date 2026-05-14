import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.schemas.payment import PaymentInitiate, PaymentResponse
from app.services import payment_service

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post(
    "/initiate",
    response_model=dict,
    status_code=201,
    summary="Iniciar pago con Stripe",
    description="""
Inicia el proceso de pago para una reserva existente en estado `pending`.

El sistema crea una Stripe Checkout Session y retorna:
- `checkout_url`: URL a la que se debe redirigir al usuario para completar el pago
- `session_id`: ID de la sesión Stripe
- `payment_id`: ID del pago creado en el sistema

**Flujo completo:**
1. Crear reserva → `POST /reservations`
2. Iniciar pago → `POST /payments/initiate` → obtener `checkout_url`
3. Redirigir al usuario a `checkout_url`
4. Stripe redirige al usuario de vuelta al frontend y envía webhook → `POST /payments/webhook`

**Ambiente de pruebas:**
- Número de tarjeta: `4242 4242 4242 4242`
- Fecha: cualquier fecha futura
- CVC: cualquier 3 dígitos

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
            "checkout_url": payment._checkout_url,
            "session_id": payment.token,
        },
    }


@router.post(
    "/webhook",
    response_model=dict,
    summary="Webhook de Stripe",
    description="""
Endpoint que Stripe llama automáticamente al completar o expirar un pago.

Verifica la firma `Stripe-Signature` del header para autenticar el evento.
Maneja los siguientes eventos:
- `checkout.session.completed`: `payment.status = paid`, `reservation.status = confirmed`
- `checkout.session.expired`: `payment.status = failed`, `reservation.status = cancelled`

**Este endpoint NO requiere autenticación JWT** — es llamado directamente por Stripe.

Configurar en el dashboard de Stripe: `POST https://tu-dominio.com/api/v1/payments/webhook`
""",
)
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    await payment_service.handle_webhook(payload, sig_header, session)
    return {"received": True}


@router.get(
    "/{payment_id}",
    response_model=dict,
    summary="Ver estado de un pago",
    description="""
Retorna el detalle y estado actual de un pago.

Estados posibles:
- `initiated`: sesión Stripe creada, usuario aún no completó el pago
- `paid`: pago confirmado exitosamente por Stripe
- `failed`: pago rechazado o sesión expirada
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
