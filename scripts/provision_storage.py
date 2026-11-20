"""Provision/connect only dedicated batteryflex-mvp resources; never migrate on startup."""

from batteryflex.storage.provision import provision
from batteryflex.storage.settings import ROOT

if __name__ == "__main__":
    try:
        provision(ROOT / ".env")
        print(
            "Dedicated database/bucket connections verified; local .env updated securely. "
            "Run storage_admin.py bootstrap next."
        )
    except ValueError as exc:
        print(f"Setup required: {exc}")
        raise SystemExit(1) from None
    except Exception:
        print(
            "Provisioning could not be verified. Check dedicated resource permissions; "
            "no credentials logged."
        )
        raise SystemExit(1) from None
