"""Small common SQL interface: local SQLite and parameterized Turso Hrana transactions."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

Statement = tuple[str, tuple[Any, ...]]


class Database(Protocol):
    def batch(self, statements: list[Statement]) -> list[list[dict[str, Any]]]: ...


class SQLiteDatabase:
    def __init__(self, path: Path, *, create: bool = False):
        self.path = path
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            raise ValueError(
                "Local storage is not bootstrapped. Run the storage bootstrap command."
            )

    def batch(self, statements: list[Statement]) -> list[list[dict[str, Any]]]:
        try:
            with sqlite3.connect(self.path, timeout=30) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("BEGIN IMMEDIATE")
                return [
                    [dict(row) for row in connection.execute(sql, args).fetchall()]
                    for sql, args in statements
                ]
        except sqlite3.Error as exc:
            code = getattr(exc, "sqlite_errorname", "SQLITE_ERROR")
            raise ValueError(
                f"Local SQL transaction failed ({code}); changes were not committed"
            ) from None


def _value(value: Any) -> dict:
    if value is None:
        return {"type": "null"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


class TursoDatabase:
    def __init__(self, url: str, token: str, *, read_only: bool = False):
        parsed = urlparse(url.replace("libsql://", "https://"))
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or not parsed.hostname.startswith("batteryflex-mvp-")
            or not parsed.hostname.endswith(".turso.io")
            or parsed.username
            or parsed.query
            or parsed.path not in ("", "/")
        ):
            raise ValueError("Turso must target the dedicated batteryflex-mvp database")
        self.endpoint = f"https://{parsed.hostname}/v2/pipeline"
        self.token = token
        self.read_only = read_only

    def batch(self, statements: list[Statement]) -> list[list[dict[str, Any]]]:
        # Every write is conditional on all earlier steps. COMMIT is skipped on any error;
        # closing the stream rolls back an uncommitted transaction.
        steps = []
        if self.read_only and any(
            not sql.lstrip().upper().startswith("SELECT ") for sql, _ in statements
        ):
            raise ValueError("The public demonstration only permits storage reads")
        sqls = (
            statements
            if self.read_only
            else [
                ("PRAGMA foreign_keys=ON", ()),
                ("BEGIN IMMEDIATE", ()),
                *statements,
                ("COMMIT", ()),
            ]
        )
        for i, (sql, args) in enumerate(sqls):
            step: dict[str, Any] = {
                "stmt": {"sql": sql, "args": [_value(a) for a in args], "want_rows": True}
            }
            if i:
                step["condition"] = {
                    "type": "and",
                    "conds": [{"type": "ok", "step": j} for j in range(i)],
                }
            steps.append(step)
        body = json.dumps(
            {"requests": [{"type": "batch", "batch": {"steps": steps}}, {"type": "close"}]}
        ).encode()
        request = Request(
            self.endpoint,
            data=body,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=45) as response:
                data = json.load(response)
        except HTTPError as exc:
            raise ValueError(f"Dedicated Turso request failed (HTTP {exc.code})") from None
        except (URLError, TimeoutError):
            raise ValueError("Dedicated Turso is unreachable") from None
        response = data["results"][0]
        if response["type"] != "ok":
            raise ValueError("Turso transaction failed")
        result = response["response"]["result"]
        if any(result["step_errors"]):
            raise ValueError("Turso transaction rejected; no changes committed")
        rows = []
        results = result["step_results"]
        for stmt in results if self.read_only else results[2:-1]:
            rows.append(
                [
                    {
                        c["name"]: (
                            None
                            if v["type"] == "null"
                            else int(v["value"])
                            if v["type"] == "integer"
                            else v["value"]
                        )
                        for c, v in zip(stmt["cols"], r, strict=True)
                    }
                    for r in stmt["rows"]
                ]
            )
        return rows


def query(db: Database, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
    return db.batch([(sql, args)])[0]


def migrate(db: Database) -> None:
    files = sorted((Path(__file__).parent / "migrations").glob("*.sql"))
    # Explicit owner command only; never called by normal UI loads.
    db.batch(
        [
            (
                "CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, "
                "sha256 TEXT NOT NULL)",
                (),
            )
        ]
    )
    for path in files:
        version = int(path.stem.split("_")[0])
        content = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(content.encode()).hexdigest()
        old = query(db, "SELECT sha256 FROM schema_migrations WHERE version=?", (version,))
        if old:
            if old[0]["sha256"] != digest:
                raise ValueError("Applied migration checksum changed")
            continue
        statements = [(sql.strip(), ()) for sql in content.split(";") if sql.strip()]
        # Another initial migrator may finish first; explicit command can safely be retried.
        db.batch([*statements, ("INSERT INTO schema_migrations VALUES(?,?)", (version, digest))])


def verify_schema(db: Database) -> None:
    expected = {
        int(path.stem.split("_")[0]): hashlib.sha256(
            path.read_text(encoding="utf-8").encode()
        ).hexdigest()
        for path in (Path(__file__).parent / "migrations").glob("*.sql")
    }
    rows = query(db, "SELECT version,sha256 FROM schema_migrations")
    if {row["version"]: row["sha256"] for row in rows} != expected:
        raise ValueError("Storage schema version/checksum is incompatible; use explicit migrations")
