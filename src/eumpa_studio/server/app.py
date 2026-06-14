"""FastAPI application for eumpa_studio."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eumpa_studio.server.routes.jobs import router as jobs_router

app = FastAPI(title="eumpa_studio", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(jobs_router, prefix="/api")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
