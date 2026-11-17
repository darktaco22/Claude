#!/bin/bash
# resumable: install deps, run generator, commit + push results with retry
set -u
cd "$(dirname "$0")/../../../.." && git fetch origin claude/last-line-final && git reset --hard FETCH_HEAD
cd commercial/who-sold/voice/v2
pip install -q chatterbox-tts faster-whisper 2>&1 | tail -2
for i in 1 2 3; do python3 gen_v2.py && break; echo "retry $i"; done
cd ../../../..
git add commercial/who-sold/voice/v2/out && git commit -q -m "WHO SOLD? v2: re-recorded narrator lines" || true
for i in 1 2 3 4; do git push -u origin HEAD:claude/last-line-final && break || { git fetch origin claude/last-line-final && git rebase FETCH_HEAD; sleep $((i*3)); }; done
ls commercial/who-sold/voice/v2/out
