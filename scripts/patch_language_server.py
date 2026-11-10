#!/usr/bin/env python3
"""Patch the Antigravity 2.29.1 ARM64 language server resolver path.

2.28.2 used the cwd-relative path "etc//resolv.conf", which resolved to the
app-generated file (filesDir/etc/resolv.conf). 2.29.1 switched to the absolute
path "/etc/resolv.conf". On Android that file is not writable by the app and may
contain a loopback nameserver, so DNS fails. This rewrites the embedded string
in place, preserving its 16-byte length and all ELF offsets.

Usage:
  python3 patch_language_server.py input [--output out] [--expect 2]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys

OLD = b"/etc/resolv.conf"
NEW = b"etc//resolv.conf"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="unpatched language_server binary")
    ap.add_argument("-o", "--output", help="output path (default: <input>.dnsfix)")
    ap.add_argument(
        "--expect",
        type=int,
        default=2,
        help="expected number of resolver-path occurrences (default: 2, use 0 to disable)",
    )
    args = ap.parse_args()

    if len(OLD) != len(NEW):
        raise RuntimeError("replacement must have the same length as the original")

    with open(args.input, "rb") as f:
        data = f.read()

    count = data.count(OLD)
    if count == 0:
        print(f"error: no {OLD.decode()!r} string found in {args.input}", file=sys.stderr)
        return 1
    if args.expect and count != args.expect:
        print(
            f"error: expected {args.expect} occurrence(s), found {count}; "
            "this binary may be a different version",
            file=sys.stderr,
        )
        return 1

    patched = data.replace(OLD, NEW)
    if patched.count(OLD) != 0:
        print("error: replacement did not remove all occurrences", file=sys.stderr)
        return 1

    out = args.output or (args.input + ".dnsfix")
    with open(out, "wb") as f:
        f.write(patched)
    os.chmod(out, stat.S_IMODE(os.stat(args.input).st_mode))

    print(f"patched {count} occurrence(s)")
    print(f"input : {args.input}")
    print(f"output: {out}")
    print(f"size  : {len(patched)}")
    print(f"sha256: {sha256(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
