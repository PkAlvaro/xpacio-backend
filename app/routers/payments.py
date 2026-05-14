import uuid
from fastapi import APIRouter, Depends, Query, Request
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
    summary="Iniciar pago",
    description="""
Inicia el proceso de pago para una reserva en estado `pending`.

El campo `provider` determina el medio de pago:
- `stripe`: para clientes internacionales (tarjeta Visa/Mastercard/Amex)
- `transbank`: para clientes nacionales Chile (Webpay, tarjetas debito/credito locales)

Retorna `redirect_url` — redirigir al usuario a esa URL para completar el pago.

**Flujo Stripe:**
1. `POST /payments/initiate` con `provider: "stripe"` → obtener `redirect_url`
2. Redirigir usuario a `redirect_url` (Stripe Checkout)
3. Stripe notifica via `POST /payments/webhook`

**Flujo Transbank:**
1. `POST /payments/initiate` con `provider: "transbank"` → obtener `redirect_url` y `token`
2. Redirigir usuario a `redirect_url` (Webpay)
3. Transbank redirige de vuelta a `TRANSBANK_RETURN_URL?token_ws=...`
4. Frontend llama `POST /payments/confirm?token_ws=...`

**Tarjetas de prueba Stripe:**
- Exitoso: `4242 4242 4242 4242`
- Rechazado: `4000 0000 0000 0002`

**Credenciales Transbank (integracion):**
- Tarjeta: `4051 8856 0044 6623` | CVV: `123` | RUT: `11.111.111-1` | Clave: `123`

**Requiere autenticacion.**
""",
)
async def initiate_payment(
    data: PaymentInitiate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    payment = await payment_service.initiate_payment(data.reservation_id, user.id, data.provider, session)
    return {
        "success": True,
        "data": {
            "payment_id": str(payment.id),
            "provider": payment.provider,
            "redirect_url": payment._redirect_url,
            "token": payment.token,
        },
    }


@router.post(
    "/webhook",
    response_model=dict,
    summary="Webhook Stripe",
    description="""
Endpoint que Stripe llama al completar o expirar un pago. Verifica firma `Stripe-Signature`.

Eventos manejados:
- `checkout.session.completed` -> `payment.status = paid`, `reservation.status = confirmed`
- `checkout.session.expired` -> `payment.status = failed`, `reservation.status = cancelled`

**No requiere autenticacion JWT.**
""",
)
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    await payment_service.handle_stripe_webhook(payload, sig_header, session)
    return {"received": True}


@router.post(
    "/confirm",
    response_model=dict,
    summary="Confirmar pago Transbank (webhook)",
    description="""
Endpoint al que Transbank redirige al usuario tras completar el pago en Webpay.

Recibe `token_ws` como query parameter (lo envia Transbank en la redireccion).
Confirma la transaccion y actualiza estados:
- Exitoso: `payment.status = paid`, `reservation.status = confirmed`
- Fallido: `payment.status = failed`, `reservation.status = cancelled`

**No requiere autenticacion JWT.**
""",
)
async def confirm_transbank(
    token_ws: str = Query(..., description="Token enviado por Transbank en la redireccion"),
    session: AsyncSession = Depends(get_session),
):
    payment = await payment_service.confirm_transbank(token_ws, session)
    return {"success": True, "data": PaymentResponse.model_validate(payment).model_dump()}


@router.get(
    "/{payment_id}",
    response_model=dict,
    summary="Estado de un pago",
    description="""
Retorna el detalle y estado actual de un pago.

Estados: `initiated`, `paid`, `failed`, `refunded`.

Solo el dueno de la reserva puede consultar el pago.

**Requiere autenticacion.**
""",
)
async def get_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    payment = await payment_service.get_payment(payment_id, user.id, session)
    return {"success": True, "data": PaymentResponse.model_validate(payment).model_dump()}
