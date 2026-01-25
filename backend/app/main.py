from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import orgs, cycles, questionnaire, generate, results
from app.db.bootstrap import init_db
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    yield


app = FastAPI(title="Consulting Engine API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orgs.router, prefix="/api", tags=["organizations"])
app.include_router(cycles.router, prefix="/api", tags=["cycles"])
app.include_router(questionnaire.router, prefix="/api", tags=["questionnaire"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(results.router, prefix="/api", tags=["results"])


@app.get("/")
def root():
    return {"status": "ok", "version": "0.1.0"}
