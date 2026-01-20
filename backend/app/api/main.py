"""FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import runs, uploads, mappings, analytics, reports, questions
from app.db.database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Consulting Engine API",
    description="AI-assisted decision diagnostic system",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
app.include_router(mappings.router, prefix="/api/mappings", tags=["mappings"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(questions.router, prefix="/api/questions", tags=["questions"])


@app.get("/")
def root():
    return {"message": "Consulting Engine API", "version": "2.0.0"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}
