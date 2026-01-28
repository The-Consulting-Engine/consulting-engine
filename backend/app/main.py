import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import orgs, cycles, questionnaire, generate, results, competitors, menu
from app.db.bootstrap import init_db
from app.db.session import engine

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info("Incoming request: %s %s", request.method, request.url.path)
        try:
            response = await call_next(request)
            logger.info("Response: %s %s -> %d", request.method, request.url.path, response.status_code)
            return response
        except Exception as e:
            logger.exception("Request failed: %s %s -> %s", request.method, request.url.path, e)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    yield


app = FastAPI(title="Consulting Engine API", version="0.1.0", lifespan=lifespan)

# Add request logging middleware (before CORS so we see all requests)
app.add_middleware(LoggingMiddleware)

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
app.include_router(competitors.router, prefix="/api", tags=["competitors"])
app.include_router(menu.router, prefix="/api", tags=["menu"])


@app.get("/")
def root():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/debug/llm")
def debug_llm():
    """Debug endpoint to check LLM configuration."""
    import os
    from app.llm.client import LLMClient
    
    client = LLMClient()
    return {
        "provider": client.provider,
        "api_key_present": bool(client.api_key and client.api_key.strip()),
        "api_key_prefix": client.api_key[:10] + "..." if client.api_key and len(client.api_key) > 10 else "none",
        "env_llm_provider": os.getenv("LLM_PROVIDER", "not set"),
        "env_llm_api_key": "set" if os.getenv("LLM_API_KEY") else "not set",
        "env_openai_api_key": "set" if os.getenv("OPENAI_API_KEY") else "not set",
        "env_llm_model": os.getenv("LLM_MODEL", "not set"),
    }


@app.get("/api/debug/test-openai")
def test_openai():
    """Test OpenAI connection with a simple request."""
    import os
    from app.llm.client import LLMClient
    
    client = LLMClient()
    if client.provider != "openai":
        return {
            "status": "skipped",
            "reason": f"Provider is '{client.provider}', not 'openai'",
            "provider": client.provider
        }
    
    if not client.api_key or not client.api_key.strip():
        return {
            "status": "error",
            "reason": "API key is missing or empty",
            "api_key_present": False
        }
    
    try:
        # Test with a very simple prompt
        result = client.generate(
            prompt="Say 'Hello, OpenAI connection test successful!' in exactly those words.",
            json_mode=False
        )
        return {
            "status": "success",
            "response_preview": result[:200] if result else "empty",
            "response_length": len(result) if result else 0,
            "api_key_present": True,
            "provider": client.provider
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)[:500],
            "api_key_present": True,
            "provider": client.provider
        }
