from pydantic import computed_field, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Discord
    discord_token: str
    guild_id: int
    summary_channel_id: int

    # LLM Provider selection
    llm_provider: str = "openai"  # "openai" or "anthropic"

    # OpenAI settings (per D-01, D-02, D-03)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # Anthropic settings
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # Bot behavior
    timezone: str = "America/New_York"
    max_context_tokens: int = 120_000

    # Channel allowlist (D-08): comma-separated channel IDs in env var
    allowed_channel_ids_raw: str = Field(default="", alias="ALLOWED_CHANNEL_IDS")

    # On-demand summary defaults (D-01, D-11)
    default_summary_minutes: int = 240
    quiet_threshold: int = 5

    # Rate limiting
    summary_cooldown_seconds: int = 7200  # 2 hours default
    cooldown_exempt_user_ids_raw: str = Field(default="", alias="COOLDOWN_EXEMPT_USER_IDS")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cooldown_exempt_user_ids(self) -> list[int]:
        """Parse comma-separated user IDs exempt from cooldown."""
        raw = self.cooldown_exempt_user_ids_raw
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [int(p) for p in parts if p]

    # Overnight schedule
    overnight_start_hour: int = 22  # 10pm
    overnight_end_hour: int = 9    # 9am

    # Thread delivery (OUT-04, D-08, D-09)
    use_threads: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_channel_ids(self) -> list[int]:
        """Parse comma-separated channel IDs into a list of ints."""
        raw = self.allowed_channel_ids_raw
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [int(p) for p in parts if p]
