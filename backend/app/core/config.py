from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    crawl_tickers: str = "AAPL,NVDA"
    log_level: str = "INFO"

    @property
    def ticker_list(self) -> list[str]:
        return [t.strip() for t in self.crawl_tickers.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
