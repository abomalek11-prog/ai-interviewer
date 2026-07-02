from fastapi import APIRouter

from app.schemas.user import UserRead, UserUpdate
from app.utils.dependencies import CurrentUser, DbSession

router = APIRouter()


@router.patch("/me", response_model=UserRead)
def update_profile(payload: UserUpdate, db: DbSession, current_user: CurrentUser):
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
