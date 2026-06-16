import structlog
import resend
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def _format_clp(amount: int) -> str:
    return f"${amount:,.0f}".replace(",", ".")


def _reservation_html(
    client_name: str,
    space_name: str,
    address: str,
    date: str,
    start_time: str,
    end_time: str,
    total: int,
    reservation_id: str,
    calendar_url: str | None = None,
) -> str:
    calendar_btn = (
        f'<a href="{calendar_url}" style="display:inline-block;margin-top:12px;padding:10px 20px;'
        f'background:#f97316;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">'
        f'Agregar a Google Calendar</a>'
        if calendar_url else ""
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f9f5f1;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9f5f1;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#f97316,#fb923c);padding:32px 40px;">
            <h1 style="margin:0;color:#fff;font-size:28px;font-weight:700;letter-spacing:-0.5px;">Xpacio</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:15px;">Comprobante de reserva</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:36px 40px;">
            <p style="margin:0 0 20px;font-size:16px;color:#374151;">Hola <strong>{client_name}</strong>,</p>
            <p style="margin:0 0 28px;font-size:15px;color:#6b7280;">Tu reserva fue confirmada y el pago procesado exitosamente.</p>

            <!-- Details card -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9f5f1;border-radius:12px;padding:0;margin-bottom:28px;">
              <tr><td style="padding:24px 28px;">
                <h2 style="margin:0 0 16px;font-size:18px;color:#111827;">{space_name}</h2>
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="padding:6px 0;font-size:14px;color:#6b7280;width:40%;">📍 Dirección</td>
                    <td style="padding:6px 0;font-size:14px;color:#111827;font-weight:500;">{address}</td>
                  </tr>
                  <tr>
                    <td style="padding:6px 0;font-size:14px;color:#6b7280;">📅 Fecha</td>
                    <td style="padding:6px 0;font-size:14px;color:#111827;font-weight:500;">{date}</td>
                  </tr>
                  <tr>
                    <td style="padding:6px 0;font-size:14px;color:#6b7280;">🕐 Horario</td>
                    <td style="padding:6px 0;font-size:14px;color:#111827;font-weight:500;">{start_time} – {end_time}</td>
                  </tr>
                  <tr>
                    <td style="padding:10px 0 0;font-size:14px;color:#6b7280;border-top:1px solid #e5e7eb;">💳 Total pagado</td>
                    <td style="padding:10px 0 0;font-size:16px;color:#f97316;font-weight:700;border-top:1px solid #e5e7eb;">{_format_clp(total)}</td>
                  </tr>
                </table>
                {calendar_btn}
              </td></tr>
            </table>

            <p style="margin:0;font-size:13px;color:#9ca3af;">ID de reserva: <code style="background:#f3f4f6;padding:2px 6px;border-radius:4px;">{reservation_id}</code></p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px;border-top:1px solid #f3f4f6;">
            <p style="margin:0;font-size:12px;color:#9ca3af;text-align:center;">
              Xpacio · Plataforma de espacios bajo demanda<br>
              Si tienes dudas responde este correo o visita <a href="https://xpacio.cl" style="color:#f97316;">xpacio.cl</a>
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


async def send_reservation_confirmation(
    client_email: str,
    client_name: str,
    space_name: str,
    address: str,
    date: str,
    start_time: str,
    end_time: str,
    total: int,
    reservation_id: str,
    calendar_url: str | None = None,
) -> None:
    if not settings.RESEND_API_KEY:
        logger.warning("email_skipped", reason="RESEND_API_KEY not set")
        return

    resend.api_key = settings.RESEND_API_KEY

    try:
        resend.Emails.send({
            "from": f"Xpacio <{settings.FROM_EMAIL}>",
            "to": [client_email],
            "subject": f"✅ Reserva confirmada — {space_name}",
            "html": _reservation_html(
                client_name=client_name,
                space_name=space_name,
                address=address,
                date=date,
                start_time=start_time,
                end_time=end_time,
                total=total,
                reservation_id=reservation_id,
                calendar_url=calendar_url,
            ),
        })
        logger.info("email_sent", to=client_email, reservation_id=reservation_id)
    except Exception as e:
        logger.error("email_failed", error=str(e), reservation_id=reservation_id)
