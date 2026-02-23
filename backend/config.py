from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    FIRECRAWL_API_KEY: str = ""
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER_NAME: str = "deepresearch-results"
    CORS_ORIGINS: str = "http://localhost:5173"
    MAX_RESEARCH_DEPTH: int = 3
    MAX_CONCURRENT_LLM_CALLS: int = 10
    MAX_CONCURRENT_SEARCH_CALLS: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
