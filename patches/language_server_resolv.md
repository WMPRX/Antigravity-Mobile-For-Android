# Language server resolver patch

Target: Antigravity 2.29.1 ARM64 `language_server` (Go binary)

## Problem

The 2.29.1 binary contains the resolver path constant:

```text
/etc/resolv.conf
```

This is an absolute path. On Android the app cannot write `/etc/resolv.conf`;
the file is part of the read-only system image and may contain a loopback
nameserver (`::1`) depending on the VPN/network stack. The Go resolver then
fails with:

```text
lookup oauth2.googleapis.com on [::1]:53: connection refused
```

The 2.28.2 binary used the relative path `etc//resolv.conf`. Because the shell
starts the language server with `ProcessBuilder.directory(filesDir)`, that
resolved to the app-generated `<filesDir>/etc/resolv.conf`, which contains the
DNS servers collected by `DnsCollector`.

## Change

Replace both occurrences of the 16-byte string with an equally long relative
path:

```text
/etc/resolv.conf   (16 bytes)
etc//resolv.conf   (16 bytes, // is equivalent to /)
```

No ELF offsets, string lengths, or Go string headers change. The server now
opens `<cwd>/etc/resolv.conf`; with cwd = `filesDir` this is exactly the file
written by the Android shell.

Applied by:

```bash
python3 scripts/patch_language_server.py input/language_server-linux-arm64
```

The script asserts that it finds the expected number of occurrences (default 2)
and refuses to patch an unexpected binary. It prints the output SHA-256, which
is then written into `assets/runtime/manifest.json` by
`scripts/update_manifest_hash.py`.
