from celery.schedules import crontab
from app.workers.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "expire-pending-reservations": {
        "task": "app.workers.tasks.reservation_tasks.expire_pending_reservations",
        "schedule": 60.0,  # every minute
    },
    "transition-reservation-states": {
        "task": "app.workers.tasks.reservation_tasks.transition_reservation_states",
        "schedule": 300.0,  # every 5 minutes
    },
    "reconcile-payments": {
        "task": "app.workers.tasks.payment_tasks.reconcile_stale_payments",
        "schedule": 900.0,  # every 15 minutes
    },
}
