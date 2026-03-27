from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Discord
    discord_token: str
    guild_id: int
    summary_channel_id: int

    # LLM Provider (per D-01, D-02, D-03)
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # Bot behavior
    timezone: str = "America/New_York"
    max_context_tokens: int = 120_000
