#!/usr/bin/env bash
# Sign the release bundle with the upload keystore, ready for Play Console.
# Password is read locally and never printed or stored.
set -euo pipefail
cd "$(dirname "$0")"

KEYSTORE="futebol-quiz-upload.keystore"
ALIAS="futebol-quiz"
UNSIGNED="app/build/outputs/bundle/release/app-release.aab"
SIGNED="app-upload-v3.aab"

[[ -f "$KEYSTORE" ]] || { echo "!! $KEYSTORE not found."; exit 1; }
[[ -f "$UNSIGNED" ]] || { echo "!! $UNSIGNED not found — run ./gradlew bundleRelease first."; exit 1; }

read -rs -p "Keystore password: " PW; echo

echo ">> Signing $UNSIGNED ..."
jarsigner -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore "$KEYSTORE" \
  -storepass "$PW" -keypass "$PW" \
  -signedjar "$SIGNED" "$UNSIGNED" "$ALIAS"

unset PW

echo ">> Verifying signature..."
jarsigner -verify "$SIGNED" >/dev/null && echo "   signature OK"

echo
echo "=== upload-key SHA-256 (must match Play Console's upload certificate) ==="
keytool -printcert -jarfile "$SIGNED" | grep -i "SHA256:" | head -1

echo
echo "DONE. Upload to Play Console: android/$SIGNED"
