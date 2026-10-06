from __future__ import annotations

from fastapi import APIRouter

from autopost_api.api.v1 import batches, categories, jobs, posts, public, topics

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(categories.router)
api_router.include_router(topics.router)
api_router.include_router(batches.router)
api_router.include_router(posts.router)
api_router.include_router(jobs.router)
api_router.include_router(public.router)
