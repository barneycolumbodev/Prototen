#!/bin/bash
# Verify the project (CLAUDE.md §10.4): import, validate every script, run GUT.
# Exits non-zero on any parse error, typing warning (treated as error), or failing test.
# Usage: tools/check.sh [extra GUT args, e.g. -gselect=test_stick]
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
GODOT="${GODOT:-godot}"
LOG_DIR="${LOG_DIR:-/tmp/graft-check}"
mkdir -p "$LOG_DIR"
fail=0

echo "== import"
timeout 600 "$GODOT" --headless --import >"$LOG_DIR/import.log" 2>&1
grep -E "SCRIPT ERROR|Parse Error|ERROR: Failed" "$LOG_DIR/import.log" && fail=1

echo "== validate scripts"
timeout 300 "$GODOT" --headless -s res://tools/validate_scripts.gd >"$LOG_DIR/validate.log" 2>&1
status=$?
grep -E "^(OK|FAIL)|SCRIPT ERROR|Parse Error" "$LOG_DIR/validate.log" | grep -v "^OK" | head -40
tail -n1 "$LOG_DIR/validate.log"
[ $status -eq 0 ] || fail=1

echo "== GUT"
timeout 600 "$GODOT" --headless -s addons/gut/gut_cmdln.gd -gdir=res://tests -ginclude_subdirs -gexit "$@" >"$LOG_DIR/gut.log" 2>&1
status=$?
sed 's/\x1b\[[0-9;]*m//g' "$LOG_DIR/gut.log" | grep -E "^(Tests|Passing Tests|Failing Tests|Risky|Asserts|Time)|\[Failed\]|FAILED|---- " | head -40
# GUT exits 0 when a test file fails to load, so check the log as well.
if [ $status -ne 0 ] || grep -qE "SCRIPT ERROR|Parse Error|Nothing was run|Ignoring script" "$LOG_DIR/gut.log"; then
  grep -E "SCRIPT ERROR|Parse Error|Ignoring script|Nothing was run" "$LOG_DIR/gut.log" | head -20
  fail=1
fi

if [ $fail -ne 0 ]; then echo "CHECK FAILED (logs in $LOG_DIR)"; exit 1; fi
echo "CHECK PASSED"
