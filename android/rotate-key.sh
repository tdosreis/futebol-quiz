#!/usr/bin/env bash
# One-time: generate a fresh upload keystore and re-sign the release bundle.
# The old keystore was leaked publicly, so this replaces it before publishing.
# Your password is read locally and never printed or stored.
set -euo pipefail
cd "$(dirname "$0")"

NEW_KEYSTORE="futebol-quiz-upload.keystore"
ALIAS="futebol-quiz"
UNSIGNED="app/build/outputs/bundle/release/app-release.aab"
SIGNED="app-upload.aab"

if [[ -f "$NEW_KEYSTORE" ]]; then
  echo "!! $NEW_KEYSTORE already exists — aborting so we don't overwrite it."
  exit 1
fi

echo ">> Choose a NEW keystore password (min 6 chars). You'll need this to sign future updates — save it in a password manager."
read -rs -p "New keystore password: " PW; echo
read -rs -p "Confirm password: " PW2; echo
[[ "$PW" == "$PW2" ]] || { echo "Passwords don't match."; exit 1; }

echo ">> Generating new keystore..."
keytool -genkeypair -v \
  -keystore "$NEW_KEYSTORE" -alias "$ALIAS" \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass "$PW" -keypass "$PW" \
  -dname "CN=Tiago dos Reis, O=tdosreis, L=Sao Paulo, ST=SP, C=BR"

echo ">> Signing the release bundle..."
jarsigner -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore "$NEW_KEYSTORE" \
  -storepass "$PW" -keypass "$PW" \
  -signedjar "$SIGNED" "$UNSIGNED" "$ALIAS"

unset PW PW2

echo ">> Verifying signature..."
jarsigner -verify "$SIGNED" >/dev/null && echo "   signature OK"

echo
echo "=== NEW upload-key SHA-256 (add this to assetlinks.json) ==="
keytool -printcert -jarfile "$SIGNED" | grep -i "SHA256:" | head -1

echo
echo "DONE."
echo "  New keystore : android/$NEW_KEYSTORE   (keep private — it's gitignored)"
echo "  Signed bundle: android/$SIGNED         (upload THIS to Play Console)"
