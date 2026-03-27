from pydantic import computed_field, Field
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

    # Channel allowlist (D-08): comma-separated channel IDs in env var
    allowed_channel_ids_raw: str = Field(default="", alias="ALLOWED_CHANNEL_IDS")

    # On-demand summary defaults (D-01, D-11)
    default_summary_minutes: int = 240
    quiet_threshold: int = 5

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_channel_ids(self) -> list[int]:
        """Parse comma-separated channel IDs into a list of ints."""
        raw = self.allowed_channel_ids_raw
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [int(p) for p in parts if p]
