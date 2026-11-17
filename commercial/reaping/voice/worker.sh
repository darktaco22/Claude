#!/bin/bash
# resumable: install deps, generate, commit + push results with retry
set -u
cd "$(dirname "$0")/../../.." && git fetch -q origin claude/last-line-final && git reset -q --hard FETCH_HEAD
cd commercial/reaping/voice
pip install -q chatterbox-tts faster-whisper 2>&1 | tail -2
for i in 1 2 3; do python3 gen.py && break; echo "retry $i"; done
cd ../../..
git add commercial/reaping/voice/out && git commit -q -m "THE REAPING: voice takes" || true
for i in 1 2 3 4; do git push -q origin HEAD:claude/last-line-final && break || { git fetch -q origin claude/last-line-final && git rebase -q FETCH_HEAD; sleep $((i*3)); }; done
ls commercial/reaping/voice/out
