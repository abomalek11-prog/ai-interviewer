import uuid

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.paths import UPLOADS_DIR
from app.core.security import get_password_hash, verify_password
from app.schemas.auth import MessageResponse
from app.schemas.user import ChangePasswordRequest, UserRead, UserUpdate
from app.utils.dependencies import CurrentUser, DbSession

router = APIRouter()

MAX_AVATAR_BYTES = 5 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


@router.patch("/me", response_model=UserRead)
def update_profile(payload: UserUpdate, db: DbSession, current_user: CurrentUser):
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(db: DbSession, current_user: CurrentUser, file: UploadFile) -> UserRead:
    content_type = file.content_type or ""
    extension = ALLOWED_AVATAR_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image type")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty file")
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image is too large (max 5MB)")

    avatars_dir = UPLOADS_DIR / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{current_user.id}-{uuid.uuid4().hex[:8]}{extension}"
    (avatars_dir / filename).write_bytes(content)

    current_user.profile_picture_url = f"{settings.OAUTH_REDIRECT_BASE_URL}/media/avatars/{filename}"
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=MessageResponse)
def change_password(payload: ChangePasswordRequest, db: DbSession, current_user: CurrentUser) -> MessageResponse:
    if not current_user.hashed_password or not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()
    return MessageResponse(message="Password updated")
