# Build notes

## Inputs

The build needs three proprietary inputs that are not included in this repo:

1. `REFERENCE_APK` — the original `com.agy` 2.28.2 shell APK (not an APK
   produced by this project). The port replaces its language server, web
   bundle, and `classes.dex` patch. The shell is a third-party artifact; obtain
   it from the project/author you trust.
2. `LS_BIN` — the official Antigravity 2.29.1 ARM64 language server:
   `https://storage.googleapis.com/antigravity-public/antigravity-hub/2.29.1-5241471524274176/unsigned/language_server-linux-arm64`
   SHA-256 `79c885734bd7aa10ce116ad7bd5117ca6e552501d9f412ba42c33cbca8610784`.
3. `WEB_DIR` — the 2.29.1 web bundle. It must have the layout the shell's
   `assets/web` expects: `index.html`, `generated/main.js`,
   `page_agent_bundle.js`, `page_facade_bundle.js`, `symbols-icons/`,
   `workers/`, audio files, CSS, etc.

## Toolchain

- Java 17+ (baksmali/smali, apksigner, keytool)
- Python 3
- Android build-tools 34.0.0
- `zip`, `unzip`
- baksmali/smali 2.5.x jars

On Debian/Ubuntu:

```bash
sudo apt install openjdk-17-jdk python3 zip unzip apktool
# jars are then in /usr/share/java/baksmali.jar and /usr/share/java/smali.jar
```

## zipalign on aarch64

`zipalign` from the Android SDK is an x86_64 ELF binary. The build script tries
to run it directly and then through `qemu-x86_64`. A working setup:

```bash
sudo dpkg --add-architecture amd64
# add an amd64 Ubuntu archive source if your mirror is arm64-only
sudo apt update
sudo apt install qemu-user libc6:amd64 libgcc-s1:amd64
```

If neither route works, the script stores `resources.arsc` uncompressed and
continues with a warning. The reference APK targets SDK 28; many devices accept
this, but recent Android versions may require proper alignment. Preferred:
build on an x86_64 machine or align the unsigned APK there.

## Reproducibility

The reference build produced:

```text
size   110716549
sha256 a3430ae91e3ec7b1bb63ce13edf0da7bae1159bca8acb4ec0efd7c45e7dcc170
```

This hash is from the reference build and is not guaranteed to reproduce.
`smali`/`dexlib2` does not emit deterministic DEX bytes: the same inputs can
produce different class/method ordering on each run, changing `classes.dex` and
therefore the APK SHA-256. Different keystores, `zip` implementations, or
build-tools versions also change the APK hash. The patched language server, web
bundle, and runtime manifest hash are deterministic.

## Manual steps

If you prefer to run the steps manually:

```bash
python3 scripts/patch_language_server.py "$LS_BIN" -o build/liblanguage_server.so
python3 scripts/patch_dns_collector.py --dex build/apk/classes.dex \
    --output build/classes_patched.dex \
    --baksmali /usr/share/java/baksmali.jar \
    --smali /usr/share/java/smali.jar
python3 scripts/update_manifest_hash.py \
    build/apk/assets/runtime/manifest.json build/liblanguage_server.so
```

Then repack, store `resources.arsc`, align, and sign as shown in `build.sh`.
