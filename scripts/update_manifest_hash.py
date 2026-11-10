#!/usr/bin/env python3
"""Update assets/runtime/manifest.json with a new liblanguage_server.so hash.

The shell verifies every runtime file against this manifest; changing the
language server binary without updating the hash makes the integrity check fail
(or prevents the "runtime up to date" marker from being refreshed).

Usage:
  python3 update_manifest_hash.py assets/runtime/manifest.json path/to/liblanguage_server.so
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

KEY_RE = re.compile(
    r'("bin/liblanguage_server\.so"\s*:\s*")([0-9a-fA-F]{64})(")'
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", help="assets/runtime/manifest.json")
    ap.add_argument("binary", help="new liblanguage_server.so")
    args = ap.parse_args()

    manifest = Path(args.manifest)
    binary = Path(args.binary)
    if not manifest.is_file():
        raise SystemExit(f"missing manifest: {manifest}")
    if not binary.is_file():
        raise SystemExit(f"missing binary: {binary}")

    new_hash = sha256(binary)
    text = manifest.read_text(encoding="utf-8")
    match = KEY_RE.search(text)
    if not match:
        raise SystemExit("bin/liblanguage_server.so entry not found in manifest")

    old_hash = match.group(2)
    if old_hash.lower() == new_hash:
        print(f"manifest already up to date: {new_hash}")
        return 0

    text = text[: match.start(2)] + new_hash + text[match.end(2) :]
    manifest.write_text(text, encoding="utf-8")
    print(f"manifest: {old_hash} -> {new_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
