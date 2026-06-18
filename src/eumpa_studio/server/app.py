"""FastAPI application for eumpa_studio."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eumpa_studio.server.routes.health import router as health_router
from eumpa_studio.server.routes.jobs import router as jobs_router
from eumpa_studio.server.routes.projects import router as projects_router
from eumpa_studio.server.routes.shots import router as shots_router
from eumpa_studio.server.routes.assets import router as assets_router
from eumpa_studio.server.routes.workflows import router as workflows_router
from eumpa_studio.server.routes.prompts import router as prompts_router
from eumpa_studio.server.routes.export import router as export_router
from eumpa_studio.server.routes.settings import router as settings_router

app = FastAPI(title="eumpa_studio", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(shots_router, prefix="/api")
app.include_router(assets_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(prompts_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
