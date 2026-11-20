"""Explicit immutable event-history preparation; no downloads or cloud writes."""

import argparse
from pathlib import Path

from batteryflex.event_source import prepare_history

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/lcl/event_history_v1"))
    args = parser.parse_args()
    report = prepare_history(Path.cwd(), args.output)
    print(
        {
            k: v
            for k, v in report.items()
            if k not in ("original_source", "source_members", "original_coverage")
        }
    )
