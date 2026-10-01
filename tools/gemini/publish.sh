#!/usr/bin/env bash
# Commit what the batch has painted so far to the gemini-batch branch.
# Shards run side by side and only ever add different files, so a push that
# loses the race simply rebases on the other shard's commit and goes again.
set -u
cd "${STAGE:-stage}" || exit 0
git add -A
git diff --cached --quiet && exit 0
git commit -q -m "Gemini batch: ${1:-progress} (shard ${SHARD:-0})"
for i in 1 2 3 4 5 6; do
  git pull -q --rebase origin gemini-batch && git push -q origin HEAD:gemini-batch && exit 0
  sleep $((i * 5))
done
echo "publish: could not push after retries" >&2
