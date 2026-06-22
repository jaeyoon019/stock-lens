from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: SecretStr
    openai_api_key: SecretStr
    openai_model: str = "gpt-4o-mini"
    crawl_tickers: str = "AAPL,NVDA"
    log_level: str = "INFO"

    @property
    def ticker_list(self) -> list[str]:
        return [t.strip() for t in self.crawl_tickers.split(",")]


settings = Settings()
