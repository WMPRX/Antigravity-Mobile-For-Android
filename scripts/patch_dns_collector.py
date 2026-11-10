#!/usr/bin/env python3
"""Remove loopback DNS servers from com.agy.net.DnsCollector.

The Android shell writes <filesDir>/etc/resolv.conf from the list returned by
DnsCollector.collectDnsServers(). On some devices that list contains ::1 and/or
127.0.0.1 first, which makes the bundled Go language server send DNS queries to
the loopback resolver. This patch removes those entries after the two source
lists are merged, so the existing fallback (1.1.1.1, 77.88.8.8, 8.8.8.8) is used
when no real resolver remains.

The DEX is disassembled with baksmali, patched textually, and reassembled with
smali. The patch is idempotent: if the loopback removal is already present, the
input DEX is copied to the output unchanged.

Usage:
  python3 patch_dns_collector.py --dex classes.dex --output classes_patched.dex \
      --baksmali /usr/share/java/baksmali.jar --smali /usr/share/java/smali.jar
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path("com/agy/net/DnsCollector.smali")
ANCHOR = (
    "    invoke-interface {p0, v2}, Ljava/util/List;->addAll(Ljava/util/Collection;)Z\n"
)
PATCH = (
    '\n'
    '    const-string v0, "::1"\n'
    '\n'
    '    invoke-interface {p0, v0}, Ljava/util/List;->remove(Ljava/lang/Object;)Z\n'
    '\n'
    '    const-string v0, "127.0.0.1"\n'
    '\n'
    '    invoke-interface {p0, v0}, Ljava/util/List;->remove(Ljava/lang/Object;)Z\n'
)
MARKER = 'const-string v0, "::1"'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(cmd)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dex", required=True, help="input classes.dex")
    ap.add_argument("--output", required=True, help="output classes.dex")
    ap.add_argument("--baksmali", required=True, help="path to baksmali jar")
    ap.add_argument("--smali", required=True, help="path to smali jar")
    ap.add_argument("--java", default="java", help="java executable (default: java)")
    args = ap.parse_args()

    dex = Path(args.dex)
    out = Path(args.output)
    for p in (dex, Path(args.baksmali), Path(args.smali)):
        if not p.is_file():
            raise SystemExit(f"missing file: {p}")

    with tempfile.TemporaryDirectory(prefix="agy-dex-") as tmp:
        tmpdir = Path(tmp)
        smali_dir = tmpdir / "smali"
        run([args.java, "-jar", args.baksmali, "d", str(dex), "-o", str(smali_dir)])

        target = smali_dir / TARGET
        if not target.is_file():
            raise SystemExit(f"class not found in DEX: {TARGET}")

        text = target.read_text(encoding="utf-8")
        if MARKER in text:
            print("DnsCollector is already patched; copying input DEX")
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(dex, out)
        else:
            count = text.count(ANCHOR)
            if count != 1:
                raise SystemExit(
                    f"unexpected anchor count in {TARGET}: {count} (expected 1); "
                    "the APK/class version may be different"
                )
            patched = text.replace(ANCHOR, ANCHOR + PATCH, 1)
            target.write_text(patched, encoding="utf-8")

            out.parent.mkdir(parents=True, exist_ok=True)
            if out.exists():
                out.unlink()
            run([args.java, "-jar", args.smali, "a", str(smali_dir), "-o", str(out)])

    print(f"output: {out}")
    print(f"size  : {out.stat().st_size}")
    print(f"sha256: {sha256(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
