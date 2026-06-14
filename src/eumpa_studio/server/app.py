"""FastAPI application for eumpa_studio."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eumpa_studio.config import get_settings
from eumpa_studio.server.routes.health import router as health_router

app = FastAPI(title="eumpa_studio", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.settings = get_settings()

app.include_router(health_router, prefix="/api")
