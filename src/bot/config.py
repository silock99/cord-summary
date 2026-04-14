import json
import logging
from pathlib import Path

from pydantic import computed_field, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    # Admin user IDs (comma-separated) — receive error DMs, can use /post-summary, exempt from cooldown
    admin_user_ids_raw: str = Field(default="", alias="ADMIN_USER_IDS")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def admin_user_ids(self) -> list[int]:
        """Parse comma-separated admin user IDs."""
        raw = self.admin_user_ids_raw
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [int(p) for p in parts if p]

    # CFBD/CBBD API keys (Phase 9: Career Stats)
    cfbd_api_key: str = ""
    cbbd_api_key: str = ""

    # Recruiting editor IDs (comma-separated) -- per D-11, INFRA-05
    recruiting_editor_ids_raw: str = Field(default="", alias="RECRUITING_EDITOR_IDS")

    # Channel-to-sport mapping (comma-separated) -- per D-14, INFRA-04
    football_channel_ids_raw: str = Field(default="", alias="FOOTBALL_CHANNEL_IDS")
    basketball_channel_ids_raw: str = Field(default="", alias="BASKETBALL_CHANNEL_IDS")

    # Overnight schedule
    overnight_start_hour: int = 22  # 10pm
    overnight_end_hour: int = 9    # 9am

    # Thread delivery (OUT-04, D-08, D-09)
    use_threads: bool = False

    # Phase 13 / D-09, D-11, D-12: Google Sheets for basketball transfer targets
    sheet_service_account_json_raw: str = Field(default="", alias="SHEET_SERVICE_ACCOUNT_JSON")
    sheet_service_account_file: str = Field(default="", alias="SHEET_SERVICE_ACCOUNT_FILE")
    transfer_target_sheet_id: str = Field(
        default="1wnI1UQ_YvSXuQUS7AqCNb2tp_1Gf45zUPYPX3FiPMog",
        alias="TRANSFER_TARGET_SHEET_ID",
    )
    transfer_target_sheet_tab: str = Field(
        default="Master List 2025",
        alias="TRANSFER_TARGET_SHEET_TAB",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sheet_service_account_info(self) -> dict | None:
        """Resolve Google service account credentials from env (inline JSON) or file.

        Returns None if unconfigured or unparseable. On JSONDecodeError, logs ONLY
        a fixed message — never the raw value or exception text (may contain key
        fragments) per threat model T-13-01.
        """
        raw = self.sheet_service_account_json_raw
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("SHEET_SERVICE_ACCOUNT_JSON is not valid JSON")
                return None
        file_path = self.sheet_service_account_file
        if file_path:
            p = Path(file_path)
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    logger.warning("SHEET_SERVICE_ACCOUNT_FILE is not valid JSON")
                    return None
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def recruiting_editor_ids(self) -> list[int]:
        """Parse comma-separated recruiting editor user IDs."""
        raw = self.recruiting_editor_ids_raw
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [int(p) for p in parts if p]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def football_channel_ids(self) -> list[int]:
        """Parse comma-separated football channel IDs."""
        raw = self.football_channel_ids_raw
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [int(p) for p in parts if p]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def basketball_channel_ids(self) -> list[int]:
        """Parse comma-separated basketball channel IDs."""
        raw = self.basketball_channel_ids_raw
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [int(p) for p in parts if p]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_channel_ids(self) -> list[int]:
        """Parse comma-separated channel IDs into a list of ints."""
        raw = self.allowed_channel_ids_raw
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [int(p) for p in parts if p]
