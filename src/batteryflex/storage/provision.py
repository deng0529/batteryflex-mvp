"""Explicit dedicated-resource provisioning. Never called during Streamlit startup."""

import json
import os
import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import dotenv_values, set_key

from batteryflex.storage.database import TursoDatabase, query
from batteryflex.storage.objects import atomic_write


def platform_request(
    token: str, path: str, *, method: str = "GET", body: dict | None = None
) -> dict:
    request = Request(
        "https://api.turso.tech/v1/" + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            raise FileNotFoundError("Dedicated resource not found") from None
        raise ValueError(
            f"Turso platform operation denied (HTTP {exc.code}); use a platform token"
        ) from None
    except OSError:
        raise ValueError("Turso platform is unreachable") from None


def prepare_database(values: dict[str, str]) -> tuple[str, str]:
    url = values.get("BATTERYFLEX_TURSO_DATABASE_URL", "")
    token = values.get("BATTERYFLEX_TURSO_AUTH_TOKEN", "")
    if url and token:
        query(TursoDatabase(url, token), "SELECT 1 AS connected")
        return url, token
    # The old TURSO_AUTH_TOKEN is explicitly NOT an account-management fallback.
    manager = values.get("BATTERYFLEX_TURSO_PLATFORM_TOKEN") or values.get("TURSO_API_TOKEN")
    org = values.get("BATTERYFLEX_TURSO_ORGANIZATION") or values.get("TURSO_ORGANIZATION")
    if not manager or not org:
        raise ValueError(
            "Supply a Turso platform token (db:create/db:mint-token plus database-read permission) "
            "and organisation slug, or manually create batteryflex-mvp "
            "and set its dedicated URL/token"
        )
    if not re.fullmatch(r"[A-Za-z0-9_-]+", org):
        raise ValueError("Invalid Turso organisation slug")
    path = f"organizations/{quote(org)}/databases/batteryflex-mvp"
    try:
        data = platform_request(manager, path)
    except FileNotFoundError:
        platform_request(
            manager,
            f"organizations/{quote(org)}/databases",
            method="POST",
            body={"name": "batteryflex-mvp", "group": values.get("TURSO_GROUP", "default")},
        )
        data = platform_request(manager, path)
    database = data["database"]
    if database["Name"] != "batteryflex-mvp":
        raise ValueError("Platform returned the wrong database identity")
    url = "libsql://" + database["Hostname"]
    # Validate isolation BEFORE minting/using a SQL token.
    TursoDatabase(url, "unused")
    token = platform_request(
        manager, path + "/auth/tokens?authorization=full-access", method="POST"
    )["jwt"]
    query(TursoDatabase(url, token), "SELECT 1 AS connected")
    return url, token


def provision(env_path: Path) -> None:
    values = {k: v for k, v in {**dotenv_values(env_path), **os.environ}.items() if v is not None}
    from boto3 import client
    from botocore.config import Config

    account = values.get("R2_ACCOUNT_ID")
    access = values.get("BATTERYFLEX_R2_ACCESS_KEY_ID") or values.get("R2_ACCESS_KEY_ID")
    secret = values.get("BATTERYFLEX_R2_SECRET_ACCESS_KEY") or values.get("R2_SECRET_ACCESS_KEY")
    if not all((account, access, secret)):
        raise ValueError(
            "Supply existing R2 account/access credentials with access to batteryflex-mvp"
        )
    s3 = client(
        "s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        region_name="auto",
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        config=Config(connect_timeout=10, read_timeout=15, retries={"max_attempts": 1}),
    )
    try:
        s3.head_bucket(Bucket="batteryflex-mvp")
    except Exception as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code")
        if code not in ("404", "NoSuchBucket"):
            raise ValueError(
                "Existing R2 keys cannot verify batteryflex-mvp. Create the bucket manually "
                "and grant those keys bucket access, or supply a suitably scoped credential"
            ) from None
        try:
            s3.create_bucket(Bucket="batteryflex-mvp")
            s3.head_bucket(Bucket="batteryflex-mvp")
        except Exception:
            raise ValueError("R2 bucket creation denied; create batteryflex-mvp manually") from None
    url, token = prepare_database(values)
    # Both safe connection reads succeeded. Preserve the existing secret file byte-for-byte.
    backup = env_path.with_name(".env.task05c.backup")
    if env_path.exists() and not backup.exists():
        atomic_write(backup, env_path.read_bytes())
    with tempfile.NamedTemporaryFile(
        dir=env_path.parent, prefix=".env.task05c.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(env_path.read_bytes() if env_path.exists() else b"")
    try:
        set_key(temporary, "BATTERYFLEX_TURSO_DATABASE_URL", url)
        set_key(temporary, "BATTERYFLEX_TURSO_AUTH_TOKEN", token)
        set_key(temporary, "BATTERYFLEX_STORAGE_MODE", "cloud")
        os.replace(temporary, env_path)
    finally:
        temporary.unlink(missing_ok=True)
