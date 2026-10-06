from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _package_root() -> Path:
    """apps/api locally, /app in Docker."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "src" / "autopost_api").exists():
            return parent
    return here.parents[min(2, len(here.parents) - 1)]


def _repo_root() -> Path:
    """Monorepo root when present (has docker-compose.yml); else package root."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "docker-compose.yml").exists():
            return parent
    return _package_root()


PACKAGE_ROOT = _package_root()
ROOT = _repo_root()
DATA_DIR = ROOT / "data"


def _env_files() -> tuple[str, ...]:
    files: list[str] = []
    for base in (ROOT, PACKAGE_ROOT, Path.cwd()):
        candidate = base / ".env"
        if candidate.exists():
            files.append(str(candidate))
    files.append(".env")
    # unique, preserve order
    return tuple(dict.fromkeys(files))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{DATA_DIR / 'autopost.db'}"
    redis_url: str = ""
    # apscheduler | celery — empty means auto: celery when redis_url set, else apscheduler
    scheduler_backend: str = ""
    anthropic_api_key: str = ""
    claude_model_generate: str = "claude-haiku-4-5"
    claude_model_recommend: str = "claude-haiku-4-5"
    claude_model_review: str = "claude-sonnet-5-5"
    min_post_chars: int = 2000
    site_public_base_url: str = "http://127.0.0.1:3847"
    timezone: str = "Asia/Seoul"
    beat_poll_seconds: int = 15
    review_sample_rate: float = 0.15
    admin_token: str = "dev-admin-token"
    cors_origins: str = "http://127.0.0.1:3847,http://localhost:3847"
    api_host: str = "0.0.0.0"
    api_port: int = 8471

    # Tistory Open API — https://tistory.github.io/document-tistory-apis/
    tistory_access_token: str = ""
    tistory_blog_name: str = ""

    # Google Blogger API v3. Prefer a refresh token; access token expires in about an hour.
    blogger_blog_id: str = ""
    blogger_access_token: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""

    # Unattended posting. Hours are interpreted in TIMEZONE.
    # AUTOPILOT_HOURS wins. AUTOPILOT_HOUR is the fallback when the list is empty.
    autopilot_enabled: bool = False
    autopilot_hours: str = "9,12,15,18"
    autopilot_hour: int = 9
    autopilot_minute: int = 0
    autopilot_channels: str = "blogger"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_mock_claude(self) -> bool:
        return not bool(self.anthropic_api_key.strip())

    @property
    def use_celery(self) -> bool:
        explicit = self.scheduler_backend.strip().lower()
        if explicit == "celery":
            return True
        if explicit == "apscheduler":
            return False
        return bool(self.redis_url.strip())

    @property
    def effective_scheduler(self) -> str:
        return "celery" if self.use_celery else "apscheduler"

    def autopilot_clock_times(self) -> list[tuple[int, int]]:
        """Local clock times for one post each. Hours come from AUTOPILOT_HOURS."""
        minute = min(59, max(0, int(self.autopilot_minute)))
        hours: list[int] = []
        for part in self.autopilot_hours.split(","):
            text = part.strip()
            if not text:
                continue
            try:
                hour = int(text)
            except ValueError:
                continue
            if 0 <= hour <= 23 and hour not in hours:
                hours.append(hour)
        if not hours:
            hour = int(self.autopilot_hour)
            if 0 <= hour <= 23:
                hours = [hour]
        return [(hour, minute) for hour in hours]

    def autopilot_time_label(self) -> str:
        clocks = ",".join(f"{hour:02d}:{minute:02d}" for hour, minute in self.autopilot_clock_times())
        return f"{clocks} {self.timezone}"

    def channel_configured(self, code: str) -> bool:
        if code == "site":
            return True
        if code == "tistory":
            return bool(self.tistory_access_token.strip() and self.tistory_blog_name.strip())
        if code == "blogger":
            has_blog = bool(self.blogger_blog_id.strip())
            has_refresh = bool(
                self.google_client_id.strip()
                and self.google_client_secret.strip()
                and self.google_refresh_token.strip()
            )
            has_access = bool(self.blogger_access_token.strip())
            return has_blog and (has_refresh or has_access)
        return False

    @property
    def configured_channels(self) -> list[str]:
        return [code for code in ("site", "tistory", "blogger") if self.channel_configured(code)]


settings = Settings()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Ensure SQLite parent directory exists for relative or absolute file URLs.
if settings.database_url.startswith("sqlite:///"):
    raw = settings.database_url.removeprefix("sqlite:///")
    db_path = Path(raw)
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.database_url = f"sqlite:///{db_path}"
