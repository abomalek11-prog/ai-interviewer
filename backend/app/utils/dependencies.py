from typing import Annotated

from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import TokenType, decode_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def _resolve_user(db: Session, token: str | None) -> User:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")

    try:
        payload = decode_token(token, TokenType.ACCESS)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc

    user = db.scalar(select(User).where(User.id == payload["sub"], User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    return _resolve_user(db, credentials.credentials if credentials else None)


def get_current_ws_user(websocket: WebSocket, db: DbSession) -> User:
    token = websocket.query_params.get("token")
    return _resolve_user(db, token)


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentWsUser = Annotated[User, Depends(get_current_ws_user)]
