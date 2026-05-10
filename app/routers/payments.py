import uuid
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.schemas.payment import PaymentInitiate, PaymentInitiateResponse, PaymentResponse
from app.services import payment_service
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("/initiate", response_model=dict, status_code=201)
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


@router.post("/confirm", response_model=dict)
async def confirm_payment(
    token_ws: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Webhook callback de Transbank. No requiere auth JWT."""
    payment = await payment_service.confirm_payment(token_ws, session)
    return {"success": True, "data": PaymentResponse.model_validate(payment).model_dump()}


@router.get("/{payment_id}", response_model=dict)
async def get_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    payment = await payment_service.get_payment(payment_id, user.id, session)
    return {"success": True, "data": PaymentResponse.model_validate(payment).model_dump()}
