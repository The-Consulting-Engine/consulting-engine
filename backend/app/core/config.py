from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@db:5432/consulting_engine"
    llm_provider: str = "mock"
    llm_api_key: str = ""
    
    class Config:
        env_file = ".env"


settings = Settings()
