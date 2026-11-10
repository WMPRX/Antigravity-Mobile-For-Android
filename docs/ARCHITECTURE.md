# Architecture

## Components

| Component | Location in APK | Extracted to | Role |
|---|---|---|---|
| Android shell (`com.agy`) | `classes.dex`, `AndroidManifest.xml`, resources | installed app | WebView host, extractor, process supervisor |
| Runtime binary | `assets/runtime/bin/liblanguage_server.so` | `<filesDir>/runtime/bin/` | Antigravity 2.29.1 language server (ARM64) |
| glibc loader/libs | `assets/runtime/bin/ld-linux-aarch64.so.1`, `assets/runtime/lib/` | `<filesDir>/runtime/` | Runs the Go binary and compatibility shim |
| Runtime manifest | `assets/runtime/manifest.json` | `<filesDir>/runtime/manifest.json` | SHA-256 integrity list |
| Web UI | `assets/web/` | `<filesDir>/web/` | UI served by the language server |
| Network config | generated at runtime | `<filesDir>/etc/resolv.conf`, `hosts` | DNS + hosts for the Go resolver |

## Startup flow

1. `CoreLauncher.launch(runtimeManager, filesDir)`:
   - calls `runtimeManager.installCore()`
   - sets `ProcessBuilder.directory(filesDir)`
   - applies `CoreEnvironment` (`HOME=filesDir`, `TMPDIR=cacheDir`,
     `GODEBUG=netdns=go`, `SSL_CERT_FILE=runtime/certs/ca-certificates.crt`)
2. `CoreInstaller.installCore()`:
   - compares the runtime manifest hash with `<runtime>/.installed`
   - extracts `assets/runtime` and verifies every file with `ManifestVerifier`
   - extracts `assets/web` if `<web>/main.js` or the marker is missing
   - calls `runtimeManager.writeNetworkConfig()` (writes `etc/resolv.conf`)
3. The loader executes `liblanguage_server.so` with `--web_bundle_path <filesDir>/web`.
4. The WebView loads `https://127.0.0.1:<port>/`; the shell injects
   `__APP_CONFIG__`, `__AG_ENDPOINTS__`, `__AG_CSRF__`, the bridge token, and
   `generated/patches/startup_ready.js`.

## DNS path

```text
Android ConnectivityManager
        │
        ▼
DnsCollector.collectDnsServers()
        │  (IPv4 list + IPv6 list; loopback removed by this port)
        ▼
NetworkConfigWriter.write()
        ▼
<filesDir>/etc/resolv.conf
        ▲
        │  relative "etc//resolv.conf", cwd = <filesDir>
        │
language server (Go resolver, GODEBUG=netdns=go)
```

Without the language server patch, step 4 is `/etc/resolv.conf` (absolute),
which bypasses the app-generated file and can point at `::1`.

## Repack invariants

- `resources.arsc` must be stored (method 0) and 4-byte aligned for modern
  Android installers.
- `assets/runtime/manifest.json` must contain the SHA-256 of the exact
  `liblanguage_server.so` placed in the APK.
- The root `assets/web/main.js` is required by `CoreInstaller.isWebExtracted`;
  keep it identical to `assets/web/generated/main.js` if the bundle only ships
  the latter.
- The APK must be signed with a key different from the original app; updating
  an installed original requires uninstalling it first.
