"""
Google Calendar integration — Service Account (prototype).
Falla silenciosa si no hay credenciales configuradas.
TODO: migrar a OAuth 2.0 por usuario para que cada proveedor
      gestione su propio Google Calendar.
"""
import json
import asyncio
import structlog

logger = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _build_service():
    from app.config import get_settings
    settings = get_settings()

    raw = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    if not raw or raw.strip() == "{}":
        return None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        info = json.loads(raw)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.warning("calendar_init_failed", error=str(e))
        return None


def _calendar_id() -> str:
    from app.config import get_settings
    return get_settings().GOOGLE_CALENDAR_ID


async def create_event(
    reservation_id: str,
    space_name: str,
    date: str,
    start_time: str,
    end_time: str,
    total: int,
    client_email: str,
    provider_email: str,
) -> str | None:
    return await asyncio.to_thread(
        _create_event_sync,
        reservation_id, space_name, date, start_time, end_time,
        total, client_email, provider_email,
    )


def _create_event_sync(
    reservation_id, space_name, date, start_time, end_time,
    total, client_email, provider_email,
) -> str | None:
    service = _build_service()
    cal_id = _calendar_id()
    if not service or not cal_id:
        logger.warning("calendar_skipped", reason="not_configured")
        return None

    start_dt = f"{date}T{str(start_time)[:5]}:00"
    end_dt   = f"{date}T{str(end_time)[:5]}:00"

    body = {
        "summary": f"Reserva: {space_name}",
        "description": (
            f"Reserva ID: {reservation_id}\n"
            f"Espacio: {space_name}\n"
            f"Total: ${total:,} CLP"
        ),
        "start": {"dateTime": start_dt, "timeZone": "America/Santiago"},
        "end":   {"dateTime": end_dt,   "timeZone": "America/Santiago"},
        "attendees": [
            {"email": client_email},
            {"email": provider_email},
        ],
        "status": "confirmed",
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email",  "minutes": 60},
                {"method": "popup",  "minutes": 15},
            ],
        },
    }

    try:
        result = service.events().insert(
            calendarId=cal_id, body=body, sendUpdates="all"
        ).execute()
        event_id = result.get("id")
        logger.info("calendar_event_created", event_id=event_id, reservation_id=reservation_id)
        return event_id
    except Exception as e:
        logger.error("calendar_create_failed", error=str(e))
        return None


async def delete_event(event_id: str) -> None:
    await asyncio.to_thread(_delete_event_sync, event_id)


def _delete_event_sync(event_id: str) -> None:
    service = _build_service()
    cal_id = _calendar_id()
    if not service or not cal_id:
        return
    try:
        service.events().delete(calendarId=cal_id, eventId=event_id, sendUpdates="all").execute()
        logger.info("calendar_event_deleted", event_id=event_id)
    except Exception as e:
        logger.error("calendar_delete_failed", error=str(e))


async def get_event_link(event_id: str) -> str | None:
    return await asyncio.to_thread(_get_event_link_sync, event_id)


def _get_event_link_sync(event_id: str) -> str | None:
    service = _build_service()
    cal_id = _calendar_id()
    if not service or not cal_id:
        return None
    try:
        result = service.events().get(calendarId=cal_id, eventId=event_id).execute()
        return result.get("htmlLink")
    except Exception as e:
        logger.error("calendar_get_failed", error=str(e))
        return None
