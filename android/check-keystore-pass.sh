#!/usr/bin/env bash
# Test a candidate password against the upload keystore. Prints only match/no-match.
set -uo pipefail
cd "$(dirname "$0")"
KEYSTORE="futebol-quiz-upload.keystore"
ALIAS="futebol-quiz"

while :; do
  read -rs -p "Try password (empty to quit): " PW; echo
  [[ -z "$PW" ]] && { echo "bye"; exit 0; }
  if keytool -list -keystore "$KEYSTORE" -alias "$ALIAS" -storepass "$PW" >/dev/null 2>&1; then
    echo "  ✅ MATCH — this is the one. Save it in your password manager now."
    unset PW; exit 0
  else
    echo "  ❌ no"
  fi
done
