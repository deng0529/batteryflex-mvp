"""Explicit storage administration. No source downloads or forecast training."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

from batteryflex.storage.bootstrap import bootstrap
from batteryflex.storage.database import query
from batteryflex.storage.settings import ROOT, Settings, connect

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("action", choices=["verify", "bootstrap"])
parser.add_argument(
    "--local", action="store_true", help="Use the explicit local development SQLite/object store"
)
parser.add_argument("--directory", type=Path)
args = parser.parse_args()
settings = Settings.load()
if args.local:
    settings = replace(settings, mode="local", access_mode="owner")
if args.directory:
    settings = replace(settings, directory=args.directory)
try:
    if args.action == "bootstrap" and not settings.writable:
        raise ValueError("Set BATTERYFLEX_ACCESS_MODE=owner on a private operator instance")
    repository = connect(settings, create=args.action == "bootstrap")
    if settings.mode == "cloud":
        # Safe reads must succeed on BOTH dedicated resources before any migration/write.
        query(repository.db, "SELECT 1 AS connected")
        repository.objects.client.head_bucket(Bucket="batteryflex-mvp")
        print("Dedicated Turso and R2 connections verified")
    if args.action == "bootstrap":
        result = bootstrap(repository, ROOT)
        print(json.dumps(result, indent=2))
    else:
        print("Schema rows:", len(query(repository.db, "SELECT version FROM schema_migrations")))
except ValueError as exc:
    print(f"Storage command failed: {exc}")
    raise SystemExit(1) from None
except Exception as exc:
    # SDK response bodies, endpoints and auth headers are never logged.
    code = getattr(exc, "response", {}).get("Error", {}).get("Code", type(exc).__name__)
    print(f"Storage command failed ({code}); verify dedicated resource permissions.")
    raise SystemExit(1) from None
