#!/bin/sh
# run-guard.sh <hook-file-name>
#
# Runs a sibling python hook under a watchdog. stdin/stdout/stderr of the hook
# are the caller's own. If the hook runs longer than the threshold (default 5s,
# override with SENSITIVE_GUARD_TIMEOUT, in seconds) it is killed, a one-line
# reason is written to stderr, and the exit code is 2 (block). Otherwise the
# hook's own exit code is returned unchanged.
#
# The watchdog holds no caller pipes (its stdio is the null device) and is
# reaped together with its sleep child when the hook finishes in time.

hook="${1:-}"
if [ -z "$hook" ]; then
  echo "run-guard: no hook file name given; treating as deny" >&2
  exit 2
fi

case "$0" in
  */*) dir="${0%/*}" ;;
  *) dir="." ;;
esac
path="$dir/$hook"
if [ ! -f "$path" ]; then
  echo "run-guard: hook file not found ($hook); treating as deny" >&2
  exit 2
fi

limit="${SENSITIVE_GUARD_TIMEOUT:-5}"
case "$limit" in
  '' | *[!0-9.]*) limit=5 ;;
esac

# Background jobs in a non-interactive sh get the null device as stdin unless
# redirected explicitly, so keep the caller's stdin on fd 3 and hand it over.
exec 3<&0
python3 "$path" <&3 3<&- &
hook_pid=$!
exec 3<&-

(
  sleep_pid=""
  trap 'if [ -n "$sleep_pid" ]; then kill "$sleep_pid" 2>/dev/null; wait "$sleep_pid" 2>/dev/null; fi; exit 0' TERM
  sleep "$limit" &
  sleep_pid=$!
  if wait "$sleep_pid"; then
    kill -9 "$hook_pid" 2>/dev/null
  fi
) </dev/null >/dev/null 2>&1 &
wd_pid=$!

wait "$hook_pid"
rc=$?

kill "$wd_pid" 2>/dev/null
wait "$wd_pid" 2>/dev/null

if [ "$rc" -eq 137 ]; then
  echo "run-guard: analysis of $hook exceeded ${limit}s; treating as deny" >&2
  exit 2
fi
exit "$rc"
