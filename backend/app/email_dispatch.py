"""Hands over pending emails after the response has been sent (DD-04, NFR-004).

Runs with its own database connection because the request's connection is closed by then.
"""
from .db import connect
from .repositories import SqliteAccountRepository, SqliteNotificationRepository
from .services.notification_service import NotificationService


def dispatch_pending_emails(app) -> int:
    conn = connect(app.config["DATABASE_PATH"])
    try:
        clock = app.config.get("CLOCK")
        kwargs = {"clock": clock} if clock else {}
        service = NotificationService(SqliteNotificationRepository(conn), SqliteAccountRepository(conn),
                                      app.extensions["email_gateway"], **kwargs)
        return service.dispatch_pending()
    finally:
        conn.close()
