import uuid
from fastapi import APIRouter, Depends, Query, Request, Body
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.schemas.payment import PaymentInitiateStripe, PaymentInitiateTransbank, PaymentResponse
from app.services import payment_service
from app.constants import PaymentProvider

# Tres routers — Swagger los agrupa por tag
router_stripe = APIRouter(prefix="/api/v1/payments/stripe", tags=["Pagos - Stripe (internacional)"])
router_transbank = APIRouter(prefix="/api/v1/payments/transbank", tags=["Pagos - Transbank (Chile)"])
router_shared = APIRouter(prefix="/api/v1/payments", tags=["Pagos - Estado"])


# ─── STRIPE ───────────────────────────────────────────────────────────────────

@router_stripe.post(
    "/initiate",
    response_model=dict,
    status_code=201,
    summary="[Stripe] Iniciar pago internacional",
    description="""
Crea una Stripe Checkout Session para pagar con tarjeta internacional.

Devuelve `redirect_url` — abrir esa URL en el browser para completar el pago.

**Paso a paso para probar:**
1. Crear reserva → `POST /reservations` → copiar `reservation_id`
2. Ejecutar este endpoint con ese `reservation_id`
3. Abrir `redirect_url` en el browser
4. Usar tarjeta de prueba: `4242 4242 4242 4242` | CVV: `123` | fecha futura
5. Stripe enviara el evento al webhook automaticamente

**Estados resultantes:**
- Pago exitoso → `payment.status = paid` | `reservation.status = confirmed`
- Pago rechazado → tarjeta `4000 0000 0000 0002`

**Requiere autenticacion.**
""",
)
async def initiate_stripe(
    data: PaymentInitiateStripe,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    payment = await payment_service.initiate_payment(
        data.reservation_id, user.id, PaymentProvider.STRIPE, session
    )
    return {
        "success": True,
        "data": {
            "payment_id": str(payment.id),
            "provider": "stripe",
            "redirect_url": payment._redirect_url,
            "token": payment.token,
        },
    }


@router_stripe.post(
    "/webhook",
    response_model=dict,
    summary="[Stripe] Webhook de confirmacion automatica",
    description="""
Stripe llama a este endpoint automaticamente cuando el usuario completa o abandona el pago.

Verifica la firma `Stripe-Signature` del header para autenticar el evento.

**No invocar manualmente** — Stripe lo llama solo.

Para desarrollo local, usar Stripe CLI:
```
stripe listen --forward-to http://localhost/api/v1/payments/stripe/webhook
```

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


# ─── TRANSBANK ────────────────────────────────────────────────────────────────

@router_transbank.post(
    "/initiate",
    response_model=dict,
    status_code=201,
    summary="[Transbank] Iniciar pago nacional (Webpay)",
    description="""
Crea una transaccion en Transbank WebpayPlus para pagar con tarjeta chilena (debito o credito).

Devuelve `redirect_url` — abrir esa URL en el browser para completar el pago en Webpay.

**Paso a paso para probar:**
1. Crear reserva → `POST /reservations` → copiar `reservation_id`
2. Ejecutar este endpoint con ese `reservation_id`
3. Abrir `redirect_url` en el browser
4. Usar credenciales de integracion (ver abajo)
5. Transbank redirige de vuelta con `?token_ws=...` en la URL
6. Copiar ese `token_ws` y ejecutar `POST /transbank/confirm?token_ws=...`

**Credenciales de integracion (no se cobra dinero real):**

| Campo | Valor |
|-------|-------|
| Numero de tarjeta | `4051 8856 0044 6623` |
| CVV | `123` |
| RUT | `11.111.111-1` |
| Clave | `123` |

**Requiere autenticacion.**
""",
)
async def initiate_transbank(
    data: PaymentInitiateTransbank,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    payment = await payment_service.initiate_payment(
        data.reservation_id, user.id, PaymentProvider.TRANSBANK, session
    )
    return {
        "success": True,
        "data": {
            "payment_id": str(payment.id),
            "provider": "transbank",
            "redirect_url": payment._redirect_url,
            "token": payment.token,
        },
    }


@router_transbank.post(
    "/confirm",
    response_model=dict,
    summary="[Transbank] Confirmar pago (paso 2 obligatorio)",
    description="""
Confirma la transaccion con Transbank despues de que el usuario pago en Webpay.

**Cuando invocar:**
Transbank redirige al usuario a `TRANSBANK_RETURN_URL?token_ws=<TOKEN>`.
El frontend extrae ese `token_ws` de la URL y llama a este endpoint.

**Para probar manualmente en Swagger:**
1. Completar el flujo en Webpay (abrir `redirect_url` del endpoint anterior)
2. Copiar el `token_ws` de la URL de retorno
3. Pegarlo en el campo `token_ws` de este endpoint y ejecutar

**Resultado:**
- `response_code = 0` → `payment.status = paid` | `reservation.status = confirmed`
- `response_code != 0` → `payment.status = failed` | `reservation.status = cancelled`

**No requiere autenticacion JWT.**
""",
)
async def confirm_transbank(
    token_ws: str = Query(
        ...,
        description="Token recibido de Transbank en la URL de retorno (?token_ws=...)",
        example="e9d555262736cf3d3cecdb0a26e027d4",
    ),
    session: AsyncSession = Depends(get_session),
):
    payment = await payment_service.confirm_transbank(token_ws, session)
    return {"success": True, "data": PaymentResponse.model_validate(payment).model_dump()}


# ─── ESTADO ───────────────────────────────────────────────────────────────────

@router_shared.get(
    "/{payment_id}",
    response_model=dict,
    summary="Estado de un pago",
    description="""
Retorna el detalle y estado actual de un pago, independiente del proveedor.

**Estados posibles:**
- `initiated`: esperando que el usuario complete el pago
- `paid`: pago confirmado
- `failed`: pago rechazado o sesion expirada
- `refunded`: reembolsado

**Campo `provider`:** indica si fue `stripe` o `transbank`.

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
