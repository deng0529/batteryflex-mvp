"""Project-scoped credentials: never connect to the previous MVP resources."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

from batteryflex.storage.database import SQLiteDatabase, TursoDatabase, verify_schema
from batteryflex.storage.objects import Objects
from batteryflex.storage.repository import Repository

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    mode: str = "cloud"
    url: str = ""
    token: str = field(default="", repr=False)
    account: str = ""
    access: str = field(default="", repr=False)
    secret: str = field(default="", repr=False)
    directory: Path = ROOT / "outputs" / "persistent_storage"
    access_mode: str = "owner"
    require_cloud_credentials: bool = False

    def __post_init__(self) -> None:
        if self.access_mode not in {"demo", "owner"}:
            raise ValueError("BATTERYFLEX_ACCESS_MODE must be demo or owner")
        if self.mode not in {"cloud", "local"}:
            raise ValueError("BATTERYFLEX_STORAGE_MODE must be cloud or local")
        if self.mode == "local" and self.access_mode == "demo":
            raise ValueError("The public demonstration requires dedicated cloud storage")

    @property
    def writable(self) -> bool:
        return self.access_mode == "owner"

    def validate_cloud(self) -> None:
        if self.mode == "cloud" and not all(
            (self.url, self.token, self.account, self.access, self.secret)
        ):
            raise ValueError(
                "Dedicated Turso/R2 credentials are missing. See the deployment guide."
            )

    @classmethod
    def load(cls) -> "Settings":
        # Snapshot environment overrides before Streamlit exports root secrets to os.environ.
        from streamlit import secrets

        environment = dict(os.environ)
        try:
            hosted = dict(secrets.get("batteryflex", {}))
        except FileNotFoundError:
            hosted = {}
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid BatteryFlex secrets configuration") from exc
        values = {
            k: v
            for k, v in {**dotenv_values(ROOT / ".env"), **hosted, **environment}.items()
            if v is not None
        }
        mode = values.get("BATTERYFLEX_STORAGE_MODE", "cloud")
        access = values.get("BATTERYFLEX_ACCESS_MODE", "owner" if mode == "local" else "demo")
        return cls(
            mode,
            values.get("BATTERYFLEX_TURSO_DATABASE_URL", ""),
            values.get("BATTERYFLEX_TURSO_AUTH_TOKEN", ""),
            values.get("R2_ACCOUNT_ID", ""),
            values.get("BATTERYFLEX_R2_ACCESS_KEY_ID") or values.get("R2_ACCESS_KEY_ID", ""),
            values.get("BATTERYFLEX_R2_SECRET_ACCESS_KEY")
            or values.get("R2_SECRET_ACCESS_KEY", ""),
            Path(
                values.get(
                    "BATTERYFLEX_STORAGE_DIRECTORY", str(ROOT / "outputs/persistent_storage")
                )
            ),
            access,
            bool(hosted) or "BATTERYFLEX_ACCESS_MODE" in values,
        )


def connect(settings: Settings, *, create: bool = False) -> Repository:
    if settings.mode == "local":
        return Repository(
            SQLiteDatabase(settings.directory / "batteryflex.sqlite", create=create),
            Objects(settings.directory / "objects-cache"),
        )
    settings.validate_cloud()
    from boto3 import client
    from botocore.config import Config

    db = TursoDatabase(settings.url, settings.token, read_only=not settings.writable)
    s3 = client(
        "s3",
        endpoint_url=f"https://{settings.account}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.access,
        aws_secret_access_key=settings.secret,
        region_name="auto",
        config=Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 2}),
    )
    return Repository(
        db,
        Objects(settings.directory / "objects-cache", s3, read_only=not settings.writable),
        writable=settings.writable,
    )


def runtime_repository() -> tuple[Repository | None, str]:
    settings = Settings.load()
    if settings.mode == "cloud" and not settings.url and not settings.require_cloud_credentials:
        return None, "Cloud storage is unconfigured"
    repository = connect(settings)
    verify_schema(repository.db)
    label = "Dedicated Turso + R2" if settings.mode == "cloud" else "Local development database"
    return repository, label
