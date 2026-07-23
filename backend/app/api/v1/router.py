from fastapi import APIRouter

from app.api.v1.routers import ai, analytics, auth, candidates, interviews, jobs, oauth, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
