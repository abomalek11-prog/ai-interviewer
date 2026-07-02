import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("app.email")


class EmailService:
    """Sends transactional email via SMTP when configured, otherwise logs to console.

    Falling back to logging keeps local/dev environments usable without a mail
    provider on hand; set SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD to send for real.
    """

    def send_otp_email(self, to_email: str, code: str) -> None:
        subject = "Your InterviewAI verification code"
        body = f"Your verification code is {code}. It expires in {settings.OTP_EXPIRE_MINUTES} minutes."

        if not settings.SMTP_HOST:
            logger.info("OTP email (SMTP not configured) -> %s: %s", to_email, body)
            return

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email
        message.set_content(body)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
