from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore", populate_by_name=True)

    app_name: str = "AI Data Visualization Platform"
    secret_key: str = "dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite:///./data.db"
    upload_dir: str = "uploads"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    deepseek_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DEEPSEEK_API_KEY", "DEEPSEEK_KEY_API", "deepseek_key_api"),
    )
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    cors_origins: str = "http://localhost:5174,http://localhost:5173"
    demo_username: str = "alice"
    demo_password: str = "secret123"

    @property
    def llm_api_key(self) -> str:
        return (self.deepseek_api_key or self.openai_api_key).strip()

    @property
    def llm_base_url(self) -> str:
        if self.deepseek_api_key.strip():
            return self.deepseek_base_url.rstrip("/")
        return self.openai_base_url.rstrip("/")

    @property
    def llm_model(self) -> str:
        if self.deepseek_api_key.strip():
            return self.deepseek_model
        return self.openai_model

    @property
    def llm_provider(self) -> str:
        if self.deepseek_api_key.strip():
            return "deepseek"
        if self.openai_api_key.strip():
            return "openai"
        return "none"


settings = Settings()
