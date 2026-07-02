from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_otp_code, get_password_hash, hash_otp_code, verify_otp_code
from app.models.otp import PasswordResetOTP
from app.models.user import User
from app.services.email_service import EmailService


class PasswordResetService:
    def __init__(self, db: Session, email_service: EmailService | None = None):
        self.db = db
        self.email_service = email_service or EmailService()

    def request_otp(self, email: str) -> None:
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            # Do not reveal whether the account exists.
            return

        code = generate_otp_code()
        otp = PasswordResetOTP(
            user_id=user.id,
            code_hash=hash_otp_code(code),
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
        self.db.add(otp)
        self.db.commit()
        self.email_service.send_otp_email(user.email, code)

    def _latest_valid_otp(self, user: User) -> PasswordResetOTP | None:
        return self.db.scalar(
            select(PasswordResetOTP)
            .where(
                PasswordResetOTP.user_id == user.id,
                PasswordResetOTP.consumed_at.is_(None),
                PasswordResetOTP.expires_at > datetime.now(UTC),
            )
            .order_by(PasswordResetOTP.created_at.desc())
        )

    def verify_otp(self, email: str, code: str) -> bool:
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            return False

        otp = self._latest_valid_otp(user)
        if otp is None:
            return False
        return verify_otp_code(code, otp.code_hash)

    def reset_password(self, email: str, code: str, new_password: str) -> bool:
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            return False

        otp = self._latest_valid_otp(user)
        if otp is None or not verify_otp_code(code, otp.code_hash):
            return False

        otp.consumed_at = datetime.now(UTC)
        user.hashed_password = get_password_hash(new_password)
        self.db.add_all([otp, user])
        self.db.commit()
        return True
