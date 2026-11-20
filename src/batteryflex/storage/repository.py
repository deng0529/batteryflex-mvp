"""Immutable metadata and explicit active references on the common SQL schema."""

import json
from datetime import UTC, datetime

from batteryflex.storage.database import Database, Statement, query
from batteryflex.storage.objects import ObjectReference, Objects, sha256


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)


def now() -> str:
    return datetime.now(UTC).isoformat()


def object_statement(ref: ObjectReference) -> Statement:
    return ("INSERT INTO objects VALUES(?,?,?,?) ON CONFLICT(sha256) DO NOTHING", ref.values())


class Repository:
    def __init__(self, db: Database, objects: Objects, *, writable: bool = True):
        self.db = db
        self.objects = objects
        self.writable = writable

    def require_owner(self) -> None:
        if not self.writable:
            raise ValueError("This operation requires an owner instance")

    def setting(self, name: str):
        rows = query(self.db, "SELECT value_json FROM active_selections WHERE name=?", (name,))
        return json.loads(rows[0]["value_json"]) if rows else None

    def set_active(self, name: str, value: object) -> None:
        self.require_owner()
        self.db.batch(
            [
                (
                    "INSERT INTO active_selections VALUES(?,?) ON CONFLICT(name) "
                    "DO UPDATE SET value_json=excluded.value_json",
                    (name, canonical(value)),
                )
            ]
        )

    def reference(self, digest: str) -> ObjectReference:
        rows = query(self.db, "SELECT * FROM objects WHERE sha256=?", (digest,))
        if not rows:
            raise ValueError("Object reference is missing from database")
        return ObjectReference(**rows[0])

    def get_object(self, digest: str) -> bytes:
        return self.objects.get(self.reference(digest))

    def save_portfolio(self, payload: str) -> str:
        self.require_owner()
        from batteryflex.portfolio_storage import import_configuration

        portfolio = import_configuration(payload, reviewed_five=True)
        normalized = canonical(json.loads(payload))
        identity = sha256(normalized.encode())
        statements: list[Statement] = [
            (
                "INSERT INTO portfolios VALUES(?,?,?) ON CONFLICT(id) DO NOTHING",
                (identity, normalized, now()),
            )
        ]
        for battery in portfolio.batteries:
            row = next(
                r
                for r in json.loads(payload)["batteries"]
                if r["household_id"] == battery.household_id
            )
            statements.append(
                (
                    "INSERT INTO batteries VALUES(?,?,?) ON CONFLICT DO NOTHING",
                    (identity, battery.household_id, canonical(row)),
                )
            )
        statements.append(
            (
                "INSERT INTO active_selections VALUES('portfolio',?) ON CONFLICT(name) "
                "DO UPDATE SET value_json=excluded.value_json",
                (canonical(identity),),
            )
        )
        self.db.batch(statements)
        if self.setting("portfolio") != identity:
            raise ValueError("Portfolio persistence verification failed")
        return identity

    def portfolio(self):
        from batteryflex.portfolio_storage import import_configuration

        identity = self.setting("portfolio")
        rows = query(self.db, "SELECT config_json FROM portfolios WHERE id=?", (identity,))
        if not rows:
            raise ValueError("No active saved portfolio in database; bootstrap is required")
        return import_configuration(rows[0]["config_json"], reviewed_five=True)
