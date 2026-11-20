"""Explicit publisher download for Task 05D; never called at application startup."""

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

url = "https://data.london.gov.uk/download/smartmeter-energy-use-data-in-london-households/04feba67-f1a3-4563-98d0-f3071e3d56d1/Partitioned%20LCL%20Data.zip"
folder = Path("data/lcl/task05d-source")
folder.mkdir(parents=True, exist_ok=True)
path = folder / "PartitionedLCLData.zip"
if path.exists():
    with path.open("rb") as existing:
        existing_hash = hashlib.file_digest(existing, "sha256").hexdigest()
    if existing_hash != "149a6a9c43c622fd0a14b7d11be055665317d3018d9fb7e1043bd51420bfaea5":
        raise ValueError("Existing archive does not match the reviewed Task 05D source")
    print("Existing original archive verified; no download")
    raise SystemExit(0)
req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/zip"})
size = 0
last = 0
digest = hashlib.sha256()
start = time.monotonic()
with urlopen(req, timeout=60) as r, path.with_suffix(".part").open("wb") as output:
    meta = dict(
        url=url,
        resolved_url=r.url,
        etag=r.headers.get("ETag"),
        last_modified=r.headers.get("Last-Modified"),
        declared_bytes=r.headers.get("Content-Length"),
        acquired_at=datetime.now(UTC).isoformat(),
    )
    while True:
        block = r.read(4 * 1024 * 1024)
        if not block:
            break
        if not size and block[:4] != b"PK\x03\x04":
            raise ValueError("Publisher did not return a ZIP")
        size += len(block)
        digest.update(block)
        output.write(block)
        if size - last >= 100 * 1024 * 1024:
            last = size
            print(
                f"Original archive acquired: {size / 1024 / 1024:.0f} MiB "
                f"in {time.monotonic() - start:.1f}s",
                flush=True,
            )
    if meta["declared_bytes"] and int(meta["declared_bytes"]) != size:
        raise ValueError("Truncated download")
meta.update(
    bytes=size,
    sha256=digest.hexdigest(),
    publisher_checksum="not supplied; local SHA256 and ZIP member CRC verification recorded",
)
if digest.hexdigest() != "149a6a9c43c622fd0a14b7d11be055665317d3018d9fb7e1043bd51420bfaea5":
    raise ValueError("Publisher source changed; review it before preparing history")
path.with_suffix(".part").replace(path)
(folder / "acquisition.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
print("Original archive acquisition complete:", size, flush=True)
