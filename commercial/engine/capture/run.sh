#!/bin/bash
# usage: run.sh 'js code'   -> waits for result
cd "$(dirname "$0")"; rm -f result.txt; printf '%s' "$1" > cmd.js
for i in $(seq 1 600); do [ -f result.txt ] && { cat result.txt; echo; exit 0; }; sleep 0.5; done; echo TIMEOUT
