#!/usr/bin/env python3
"""Upload a static-export asset directory to S3-compatible object storage.

Cloudflare R2 exposes an S3-compatible API, so this helper keeps the public
GitHub Pages artifact small while serving large Trace payloads and task assets
from object storage. Credentials are read from the standard AWS environment
variables or explicit CLI flags; no secrets are stored in the repository.
"""

from __future__ import annotations

import argparse
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return guessed
    if path.suffix == ".json":
        return "application/json"
    return "application/octet-stream"


def _iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and not path.name.startswith(".DS_Store"))


def _remote_key(prefix: str, root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    prefix = prefix.strip("/")
    return f"{prefix}/{rel}" if prefix else rel


def _needs_upload(client, bucket: str, key: str, path: Path) -> bool:
    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return True
        raise
    content_length = head.get("ContentLength")
    remote_size = int(content_length) if content_length is not None else -1
    return remote_size != path.stat().st_size


def _upload_one(client, bucket: str, key: str, path: Path, *, dry_run: bool) -> tuple[str, int, str]:
    size = path.stat().st_size
    if not _needs_upload(client, bucket, key, path):
        return key, size, "skip"
    if dry_run:
        return key, size, "dry-run"
    client.upload_file(
        str(path),
        bucket,
        key,
        ExtraArgs={
            "ContentType": _content_type(path),
            "CacheControl": "public, max-age=31536000, immutable",
        },
    )
    return key, size, "upload"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload UniClawBench static assets to R2/S3.")
    parser.add_argument("--root", required=True, help="Asset directory produced by webui/export_static.py --asset-out.")
    parser.add_argument("--bucket", default=_env("R2_BUCKET") or _env("S3_BUCKET"), help="R2/S3 bucket name.")
    parser.add_argument("--prefix", default=_env("R2_PREFIX") or _env("S3_PREFIX"), help="Optional object key prefix.")
    parser.add_argument("--endpoint-url", default=_env("R2_ENDPOINT_URL") or _env("AWS_ENDPOINT_URL"), help="S3 endpoint URL.")
    parser.add_argument("--access-key-id", default=_env("R2_ACCESS_KEY_ID") or _env("AWS_ACCESS_KEY_ID"), help="Access key id.")
    parser.add_argument("--secret-access-key", default=_env("R2_SECRET_ACCESS_KEY") or _env("AWS_SECRET_ACCESS_KEY"), help="Secret access key.")
    parser.add_argument("--workers", type=int, default=16, help="Concurrent upload workers.")
    parser.add_argument("--dry-run", action="store_true", help="List objects that would upload without writing them.")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"asset root does not exist: {root}")
    missing = [name for name in ("bucket", "endpoint_url", "access_key_id", "secret_access_key") if not getattr(args, name)]
    if missing:
        raise SystemExit(f"missing required settings: {', '.join(missing)}")

    client = boto3.client(
        "s3",
        endpoint_url=args.endpoint_url,
        aws_access_key_id=args.access_key_id,
        aws_secret_access_key=args.secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 8, "mode": "standard"}),
    )

    files = _iter_files(root)
    uploaded = skipped = planned = bytes_total = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [
            pool.submit(_upload_one, client, args.bucket, _remote_key(args.prefix, root, path), path, dry_run=args.dry_run)
            for path in files
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            key, size, status = future.result()
            bytes_total += size
            if status == "upload":
                uploaded += 1
            elif status == "skip":
                skipped += 1
            else:
                planned += 1
            if index % 250 == 0 or index == len(files):
                print(
                    f"{index}/{len(files)} checked · uploaded={uploaded} "
                    f"planned={planned} skipped={skipped} bytes={bytes_total:,}",
                    flush=True,
                )

    print(
        f"done: files={len(files)} uploaded={uploaded} planned={planned} "
        f"skipped={skipped} bytes={bytes_total:,}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
