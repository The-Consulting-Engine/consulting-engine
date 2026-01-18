"""FastAPI application main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import ingest, analyze, initiatives, reports, run, context

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
app.include_router(analyze.router, prefix="/analyze", tags=["analysis"])
app.include_router(initiatives.router, prefix="/initiatives", tags=["initiatives"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(run.router, prefix="/run", tags=["run"])
app.include_router(context.router, prefix="/context", tags=["context"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Consulting Engine API", "version": settings.api_version}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


