#!/usr/bin/env bash
# Antigravity 2.29.1 Android ARM64 rebuild script.
# This script only contains original porting/build logic. It expects the
# proprietary Antigravity components to be supplied by the user.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$ROOT/config.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/config.env"
fi

abspath() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s\n' "$ROOT/$1" ;;
  esac
}

: "${REFERENCE_APK:=input/antigravity-region-bypass.apk}"
: "${LS_BIN:=input/language_server-linux-arm64-2.29.1}"
: "${WEB_DIR:=input/web}"
: "${OUT_APK:=out/antigravity-2.29.1-arm64.apk}"
: "${BUILD_DIR:=build}"
: "${KEYSTORE:=keys/antigravity.keystore}"
: "${KS_ALIAS:=antigravity}"
: "${KS_PASS:=antigravity}"
: "${BT:=/opt/android-sdk/build-tools/34.0.0}"
: "${BAKSMALI_JAR:=/usr/share/java/baksmali.jar}"
: "${SMALI_JAR:=/usr/share/java/smali.jar}"

REFERENCE_APK="$(abspath "$REFERENCE_APK")"
LS_BIN="$(abspath "$LS_BIN")"
WEB_DIR="$(abspath "$WEB_DIR")"
OUT_APK="$(abspath "$OUT_APK")"
BUILD_DIR="$(abspath "$BUILD_DIR")"
KEYSTORE="$(abspath "$KEYSTORE")"

ZIPALIGN="$BT/zipalign"
APKSIGNER="$BT/apksigner"
WORK="$BUILD_DIR/apk"
UNSIGNED="$BUILD_DIR/unsigned.apk"
ALIGNED="$BUILD_DIR/aligned.apk"
PATCHED_LS="$BUILD_DIR/liblanguage_server.so"
PATCHED_DEX="$BUILD_DIR/classes_patched.dex"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
need() { [[ -e "$1" ]] || die "missing: $1"; }

need "$REFERENCE_APK"
need "$LS_BIN"
need "$WEB_DIR"
[[ -d "$WEB_DIR" ]] || die "WEB_DIR is not a directory: $WEB_DIR"
[[ -x "$APKSIGNER" ]] || die "apksigner not found: $APKSIGNER"
[[ -f "$BAKSMALI_JAR" ]] || die "baksmali jar not found: $BAKSMALI_JAR"
[[ -f "$SMALI_JAR" ]] || die "smali jar not found: $SMALI_JAR"
command -v java >/dev/null || die "java not found"
command -v keytool >/dev/null || die "keytool not found"
command -v zip >/dev/null || die "zip not found"
command -v unzip >/dev/null || die "unzip not found"
command -v python3 >/dev/null || die "python3 not found"

rm -rf "$WORK"
mkdir -p "$WORK" "$BUILD_DIR" "$(dirname "$OUT_APK")"

printf '==> unpacking reference APK\n'
(
  cd "$WORK"
  unzip -q "$REFERENCE_APK"
)
rm -rf "$WORK/META-INF"

printf '==> patching DnsCollector (loopback DNS removal)\n'
python3 "$ROOT/scripts/patch_dns_collector.py" \
  --dex "$WORK/classes.dex" \
  --output "$PATCHED_DEX" \
  --baksmali "$BAKSMALI_JAR" \
  --smali "$SMALI_JAR"
cp "$PATCHED_DEX" "$WORK/classes.dex"
chmod 0644 "$WORK/classes.dex"

printf '==> patching language server (/etc/resolv.conf -> etc//resolv.conf)\n'
python3 "$ROOT/scripts/patch_language_server.py" "$LS_BIN" -o "$PATCHED_LS"
cp "$PATCHED_LS" "$WORK/assets/runtime/bin/liblanguage_server.so"
chmod 0755 "$WORK/assets/runtime/bin/liblanguage_server.so"

printf '==> updating runtime manifest hash\n'
python3 "$ROOT/scripts/update_manifest_hash.py" \
  "$WORK/assets/runtime/manifest.json" \
  "$PATCHED_LS"

printf '==> installing web bundle\n'
rm -rf "$WORK/assets/web"
cp -a "$WEB_DIR" "$WORK/assets/web"
if [[ ! -f "$WORK/assets/web/main.js" ]]; then
  if [[ -f "$WORK/assets/web/generated/main.js" ]]; then
    cp "$WORK/assets/web/generated/main.js" "$WORK/assets/web/main.js"
    printf '    added root main.js from generated/main.js\n'
  else
    printf '    warning: web/main.js and web/generated/main.js are both missing\n' >&2
  fi
fi
chmod -R a+rX "$WORK/assets/web"

printf '==> repacking\n'
rm -f "$UNSIGNED" "$ALIGNED" "$OUT_APK"
(
  cd "$WORK"
  zip -q -r -6 "$UNSIGNED" . -x 'resources.arsc'
  zip -q -0 "$UNSIGNED" resources.arsc
)

printf '==> aligning\n'
zipalign_works() {
  local out
  out="$(timeout 5 "$@" 2>&1 || true)"
  [[ "$out" == *"Zip alignment utility"* ]]
}

ZIPALIGN_CMD=()
if zipalign_works "$ZIPALIGN"; then
  ZIPALIGN_CMD=("$ZIPALIGN")
elif command -v qemu-x86_64 >/dev/null 2>&1 && zipalign_works qemu-x86_64 "$ZIPALIGN"; then
  ZIPALIGN_CMD=(qemu-x86_64 "$ZIPALIGN")
fi

if [[ ${#ZIPALIGN_CMD[@]} -gt 0 ]]; then
  "${ZIPALIGN_CMD[@]}" -f -p 4 "$UNSIGNED" "$ALIGNED"
  "${ZIPALIGN_CMD[@]}" -c -p 4 "$ALIGNED"
else
  printf '    warning: zipalign is unavailable; resources.arsc is stored but not aligned.\n' >&2
  printf '    warning: install qemu-user + amd64 libc, or run the build on x86_64.\n' >&2
  cp "$UNSIGNED" "$ALIGNED"
fi

printf '==> signing\n'
if [[ ! -f "$KEYSTORE" ]]; then
  mkdir -p "$(dirname "$KEYSTORE")"
  printf '    generating new keystore: %s\n' "$KEYSTORE"
  keytool -genkeypair \
    -keystore "$KEYSTORE" \
    -alias "$KS_ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -storepass "$KS_PASS" \
    -keypass "$KS_PASS" \
    -dname 'CN=Antigravity Android Port, OU=Android, O=Community, C=US'
fi

"$APKSIGNER" sign \
  --ks "$KEYSTORE" \
  --ks-key-alias "$KS_ALIAS" \
  --ks-pass "pass:$KS_PASS" \
  --key-pass "pass:$KS_PASS" \
  --v4-signing-enabled false \
  --out "$OUT_APK" \
  "$ALIGNED"

printf '==> verifying\n'
"$APKSIGNER" verify --verbose "$OUT_APK" | grep -E 'Verified using v[123] scheme|Number of signers'
if [[ ${#ZIPALIGN_CMD[@]} -gt 0 ]]; then
  "${ZIPALIGN_CMD[@]}" -c -p 4 "$OUT_APK"
fi

printf '==> done\n'
ls -l "$OUT_APK"
sha256sum "$OUT_APK"
