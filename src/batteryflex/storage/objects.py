"""Content-addressed objects with independent DB hashes and a verified disk cache."""

import hashlib
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class ObjectReference:
    sha256: str
    object_key: str
    byte_size: int
    kind: str

    def values(self) -> tuple:
        return tuple(asdict(self).values())


class ObjectStoreUnavailable(RuntimeError):
    """Remote storage could not confirm whether an object exists."""


class Objects:
    def __init__(self, cache: Path, client: Any = None, *, read_only: bool = False):
        self.cache = cache
        self.client = client
        self.read_only = read_only
        self.bucket = "batteryflex-mvp"

    def get(self, ref: ObjectReference, *, verify_remote: bool = False) -> bytes:
        if (
            ref.object_key != f"objects/{ref.sha256}"
            or len(ref.sha256) != 64
            or any(c not in "0123456789abcdef" for c in ref.sha256)
        ):
            raise ValueError("Invalid confined object reference")
        path = self.cache / ref.object_key
        if path.exists() and (not verify_remote or self.client is None):
            data = path.read_bytes()
            if sha256(data) == ref.sha256 and len(data) == ref.byte_size:
                return data
        if self.client is None:
            raise ValueError("Required local object is missing or corrupted")
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=ref.object_key)
            data = response["Body"].read()
        except Exception as exc:
            response = getattr(exc, "response", {})
            status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = response.get("Error", {}).get("Code")
            if verify_remote and status != 404 and code not in {"NoSuchKey", "NotFound"}:
                raise ObjectStoreUnavailable(
                    "R2 could not verify the result object. Retry when storage is available."
                ) from None
            raise ValueError(
                "Required R2 object is unavailable; verify dedicated bucket access"
            ) from None
        if sha256(data) != ref.sha256 or len(data) != ref.byte_size:
            raise ValueError("R2 object integrity check failed")
        atomic_write(path, data)
        return data

    def put(self, data: bytes, kind: str) -> ObjectReference:
        if self.read_only:
            raise ValueError("The public demonstration only permits object reads")
        digest = sha256(data)
        ref = ObjectReference(digest, f"objects/{digest}", len(data), kind)
        if self.client is not None:
            try:
                self.client.put_object(
                    Bucket=self.bucket, Key=ref.object_key, Body=data, IfNoneMatch="*"
                )
            except Exception as exc:
                status = (
                    getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode")
                )
                if status != 412:
                    raise ValueError("R2 upload failed; no complete model was registered") from None
            # Verify REMOTE bytes, independently of any existing local copy.
            try:
                remote = self.client.get_object(Bucket=self.bucket, Key=ref.object_key)[
                    "Body"
                ].read()
            except Exception:
                raise ValueError("R2 upload verification failed") from None
            if sha256(remote) != digest or len(remote) != len(data):
                raise ValueError("R2 uploaded object integrity mismatch")
        path = self.cache / ref.object_key
        atomic_write(path, data)
        self.get(ref)
        return ref
