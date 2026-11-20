"""Explicit, checksum-verified acquisition of the immutable 4TU v1 files."""

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

SOURCE = "https://data.4tu.nl/datasets/fbbe775b-48d8-469f-a39b-b64488bfd6fd"
DOI = "https://doi.org/10.4121/fbbe775b-48d8-469f-a39b-b64488bfd6fd.v1"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
FILES = {
    "README": ("b1787dea-0c7b-46b8-a99d-d8b17ceb6680", "710093b41c0d3258b923a6495f8bdfa3"),
    "LCL_2013_kWh.csv.zip": (
        "c0471ebc-e008-4ec4-9cff-4f12c69bafe6",
        "2a4bde340f2ee2a8aa9813debb9da363",
    ),
}


def digest(path: Path, algorithm: str = "sha256") -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def acquire(directory: Path) -> Path:
    """Download only absent files; reject damaged existing files without overwriting."""
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for name, (file_id, md5) in FILES.items():
        path = directory / name
        url = SOURCE.replace("/datasets/", "/file/") + "/" + file_id
        if not path.exists():
            temporary = path.with_suffix(path.suffix + ".part")
            try:
                with urlopen(url, timeout=120) as response, temporary.open("wb") as output:
                    shutil.copyfileobj(response, output, length=1024 * 1024)
                if digest(temporary, "md5") != md5:
                    raise ValueError(f"Publisher checksum mismatch: {name}")
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        if digest(path, "md5") != md5:
            raise ValueError(f"Existing source checksum mismatch: {name}")
        records.append(
            {
                "name": name,
                "url": url,
                "bytes": path.stat().st_size,
                "md5": md5,
                "sha256": digest(path),
            }
        )
    provenance = directory / "acquisition.json"
    if not provenance.exists():
        provenance.write_text(
            json.dumps(
                {
                    "source": SOURCE,
                    "doi": DOI,
                    "licence": LICENSE,
                    "acquired_at_utc": datetime.now(UTC).isoformat(),
                    "files": records,
                },
                indent=2,
            )
        )
    return directory / "LCL_2013_kWh.csv.zip"
