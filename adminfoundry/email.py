import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body_text: str, body_html: str | None = None) -> None:
    from adminfoundry.settings import settings

    if not settings.EMAIL_HOST:
        logger.warning("EMAIL_HOST not configured — skipping email to %s: %s", to, subject)
        return

    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_DEFAULT_FROM
        msg["To"] = to
        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as smtp:
            if settings.EMAIL_USE_TLS:
                smtp.starttls()
            if settings.EMAIL_HOST_USER:
                smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            smtp.sendmail(settings.EMAIL_DEFAULT_FROM, [to], msg.as_string())

    await asyncio.to_thread(_send)
