"""Versioned JSON download/upload persistence, with no shared server-file writes.

The browser-owned file is durable; Streamlit state is an editing workspace only.
"""

import json
from dataclasses import asdict

from batteryflex.battery import BatteryConfig
from batteryflex.portfolio import HOUSEHOLDS, Portfolio

MAX_CONFIG_BYTES = 100_000


def export_configuration(portfolio: Portfolio) -> str:
    return json.dumps(
        {"schema_version": 1, "batteries": [asdict(b) for b in portfolio.batteries]},
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )


def import_configuration(payload: str | bytes, *, reviewed_five: bool = False) -> Portfolio:
    """Reject malformed, incomplete, nonfinite and unknown-version inputs atomically."""
    if len(payload.encode() if isinstance(payload, str) else payload) > MAX_CONFIG_BYTES:
        raise ValueError("Configuration exceeds 100 kB")
    try:
        data = json.loads(payload)
        if set(data) != {"schema_version", "batteries"} or type(data["schema_version"]) is not int:
            raise ValueError("Invalid configuration envelope")
        if data["schema_version"] != 1 or not isinstance(data["batteries"], list):
            raise ValueError("Unsupported configuration schema")
        required = set(BatteryConfig.__dataclass_fields__)
        batteries = []
        for row in data["batteries"]:
            if not isinstance(row, dict) or set(row) != required:
                raise ValueError("Every battery requires exactly the version 1 fields")
            batteries.append(BatteryConfig(**row))
        portfolio = Portfolio(tuple(batteries))
        if reviewed_five:
            by_id = {b.household_id: b for b in portfolio.batteries}
            if set(by_id) != set(HOUSEHOLDS):
                raise ValueError("This page requires exactly the five reviewed LCL households")
            portfolio = Portfolio(tuple(by_id[h] for h in HOUSEHOLDS))
        return portfolio
    except (TypeError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid battery configuration: {exc}") from exc
