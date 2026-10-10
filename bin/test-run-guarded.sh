#!/usr/bin/env bash
# Tests for bin/run-guarded and bin/sysprobe. Usage: bin/test-run-guarded.sh [--no-smoke]
# All cases except the smoke run use stub system tools (first in PATH, values read from files, so
# they can change mid-run), a private lock and a temp log dir. The smoke run uses the real tools,
# the real lock and logs/guard/.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GUARD="$ROOT/bin/run-guarded"
TMP="$(mktemp -d -t byteplan-guard-test)"
trap 'rm -rf "$TMP"' EXIT
TO=(perl -e 'alarm 30; exec @ARGV') # hard timeout for every guard run

export BYTEPLAN_GUARD_LOCK="$TMP/lock" BYTEPLAN_GUARD_LOG_DIR="$TMP/logs"
export BYTEPLAN_GUARD_INTERVAL=1 BYTEPLAN_GUARD_LOG_EVERY=1 BYTEPLAN_GUARD_GRACE=2 BYTEPLAN_GUARD_FREE_WAIT=1

# --- stubs: each prints what the real tool would, from the value files in $TMP/v
REAL_PATH=$PATH
export PATH="$TMP/stubs:$PATH"
mkdir -p "$TMP/stubs" "$TMP/v"
stub() { printf "#!/bin/sh\nV='%s'\n%s\n" "$TMP/v" "$2" > "$TMP/stubs/$1"; chmod +x "$TMP/stubs/$1"; }
stub sysctl 'for k; do case $k in
  iogpu.wired_limit_mb) cat "$V/wired" ;;
  vm.swapusage) echo "total = 2048,00M  used = $(cat "$V/swap"),25M  free = 0,00M  (encrypted)" ;;
  kern.memorystatus_vm_pressure_level) cat "$V/level" ;;
  hw.memsize) echo 68719476736 ;;
esac; done'
stub vm_stat 'echo "Swapins:  0."; echo "Swapouts:  $(cat "$V/swapouts")."'
stub notifyutil 'echo "com.apple.system.thermalpressurelevel $(cat "$V/thermal")"'
stub memory_pressure 'echo "System-wide memory free percentage: $(cat "$V/free")%"'
stub df 'echo "Filesystem 1G-blocks Used Available"; echo "/dev/disk3s5 926 400 $(cat "$V/disk") /"'
stub pmset 'echo "Now drawing from $(cat "$V/power")"'
stub pgrep 'case $* in *docker*) [ "$(cat "$V/docker")" = 1 ] ;; *) exec /usr/bin/pgrep "$@" ;; esac'
val() { echo "$2" > "$TMP/v/$1"; }
defaults() {
  val wired 0; val swap 0; val level 1; val swapouts 12; val thermal 0
  val free 80; val disk 500; val power 'AC Power'; val docker 0
}
ramp() { val "$1" "$2"; (sleep 1.5; val "$1" "$3") & } # ramp NAME A B: A now, B after 1.5 s
defaults

PASS=0 FAILED=0
check() { # check NAME CONDITION...
  local name=$1; shift
  if "$@"; then PASS=$((PASS + 1)); echo "ok   $name"; else FAILED=$((FAILED + 1)); echo "FAIL $name"; fi
}
latest_log() { ls -t "$TMP"/logs/*.log | head -1; }
gone() { ! pgrep -qf "$1"; }
eq() { [ "$1" = "$2" ] || { echo "     expected '$2', got '$1'" >&2; return 1; }; }
has() { case $1 in *"$2"*) return 0 ;; esac; echo "     '$2' not in: $1" >&2; return 1; }
matches() { [[ $1 =~ $2 ]] || { echo "     '$1' does not match $2" >&2; return 1; }; }
lock_json() { # pid|profile|log dir|cmd from the lock file, which must hold exactly one JSON document
  python3 -I -c 'import json, sys; d = json.load(open(sys.argv[1]))
print(d["pid"], d["profile"], d["log"].rsplit("/", 1)[0], d["cmd"], sep="|")' "$TMP/lock"
}
lock_free() { perl -MFcntl=:flock -e 'open(my $f, ">>", shift) or exit 2; flock($f, LOCK_EX | LOCK_NB) or exit 1' "${1:-$TMP/lock}"; }

guarded() { # guarded ARGS...: run the guard, set OUT, RC, ERR
  OUT=$("${TO[@]}" "$GUARD" "$@" 2>"$TMP/err")
  RC=$?
  ERR=$(cat "$TMP/err")
}

# --- sysprobe: parses the tools' output, -1 for unreadable values
check "sysprobe: stub values" eq "$("$ROOT/bin/sysprobe")" "swap_used_mb=0 pressure_level=1 swapouts=12 thermal=0"
val swap 1536; val level 4; val swapouts 7; val thermal 2
check "sysprobe: fields in order" eq "$("$ROOT/bin/sysprobe")" "swap_used_mb=1536 pressure_level=4 swapouts=7 thermal=2"
val swap x; val level x; val swapouts x; val thermal x
check "sysprobe: unreadable -> -1" eq "$("$ROOT/bin/sysprobe")" "swap_used_mb=-1 pressure_level=-1 swapouts=-1 thermal=-1"
defaults
check "sysprobe: real tools readable" matches "$(PATH=$REAL_PATH "$ROOT/bin/sysprobe")" \
  '^swap_used_mb=[0-9]+ pressure_level=[0-9]+ swapouts=[0-9]+ thermal=[0-9]+$'

# --- usage
guarded echo x;                   check "usage: missing --" eq "$RC" 2
guarded --profile foo -- true;    check "usage: bad profile" eq "$RC" 2
guarded --;                       check "usage: no command" eq "$RC" 2

# --- preflight: one failing condition at a time, command must not run
pf() { # pf NAME VALUE_NAME VALUE (default profile: exclusive)
  defaults; val "$2" "$3"; rm -f "$TMP/ran"
  guarded -- touch "$TMP/ran"
  check "preflight $1 -> exit 3" eq "$RC" 3
  check "preflight $1 -> command not run" test ! -e "$TMP/ran"
}
pf "wired limit 60000" wired 60000
pf "swap 1024 MiB" swap 1024
pf "free 24 %" free 24
pf "pressure critical" level 4
pf "pressure unreadable" level x
pf "disk 29 GiB" disk 29
pf "on battery" power 'Battery Power'
pf "docker (exclusive)" docker 1
pf "swap unreadable" swap x
check "preflight message names the cause" has "$ERR" "swap in use: -1 MiB"
check "preflight fail logged" has "$(cat "$(latest_log)")" "end exit=3"

defaults; val wired 53248; val swap 1023; val free 25; val disk 30
guarded -- true
check "preflight boundaries pass" eq "$RC" 0
defaults; val free 80
guarded --need-gb 46 -- true
check "need-gb: 80 % of 64 GiB fits 46 + 4" eq "$RC" 0
defaults; val free 70
guarded --need-gb 46 -- true
check "need-gb: 70 % of 64 GiB too little -> exit 3" eq "$RC" 3
check "need-gb: message" has "$ERR" "not enough free RAM"
defaults; val free 70
(sleep 2; val free 80) &
BYTEPLAN_GUARD_FREE_WAIT=5 guarded --need-gb 46 -- true
wait
check "need-gb: waits for RAM released by previous run" eq "$RC" 0
guarded --need-gb x -- true
check "need-gb: non-numeric -> usage exit 2" eq "$RC" 2
defaults; val swap 8191
guarded --profile parallel -- true
check "parallel: stale swap 8191 MiB passes" eq "$RC" 0
defaults; val swap 8192
guarded --profile parallel -- true
check "parallel: swap 8192 MiB -> exit 3" eq "$RC" 3
defaults; val docker 1
guarded --profile parallel -- echo ran
check "docker (parallel) -> runs" eq "$OUT" ran
check "docker (parallel) -> warning" has "$ERR" "warning: Docker"
defaults; val power 'Battery Power'
guarded --profile parallel -- echo ran
check "battery (parallel) -> runs" eq "$OUT" ran
check "battery (parallel) -> warning" has "$ERR" "warning: on battery"
defaults

# --- exit codes and stdio pass through
guarded -- sh -c 'exit 7';        check "exit code 7 passed through" eq "$RC" 7
guarded -- false;                 check "exit code 1 passed through" eq "$RC" 1
guarded -- sh -c 'kill -TERM $$'; check "child killed by TERM -> 143" eq "$RC" 143
OUT=$(echo piped | "${TO[@]}" "$GUARD" -- cat 2>/dev/null)
check "stdin reaches the child" eq "$OUT" piped
check "lock released after run" lock_free
LOG=$(cat "$(latest_log)")
for k in " start " " preflight wired_mb=0 swap_used_mb=0 " " child " " child_exit=0" \
  " sample swap_used_mb=0 pressure_level=1 swapouts=12 thermal=0 free_pct=80" " end exit=0"; do
  check "log has '$k'" has "$LOG" "$k"
done

# --- lock: a symlinked lock path is refused and its target stays untouched
echo keep > "$TMP/victim"
ln -s "$TMP/victim" "$TMP/symlock"
rm -f "$TMP/ran"
BYTEPLAN_GUARD_LOCK="$TMP/symlock" guarded -- touch "$TMP/ran"
check "lock: symlink -> exit 5" eq "$RC" 5
check "lock: symlink target untouched" eq "$(cat "$TMP/victim")" keep
check "lock: symlink command not run" test ! -e "$TMP/ran"
# --- lock: second instance refused while the first runs; the lock file names the holder as JSON
INODE=$(stat -f %i "$TMP/lock")
CMD=(sh -c 'sleep 3 # "x\y')
printf -v WANT_CMD '%q ' "${CMD[@]}"
"${TO[@]}" "$GUARD" -- "${CMD[@]}" 2>/dev/null &
FIRST=$!
for _ in $(seq 50); do grep -q "\"pid\":$FIRST," "$TMP/lock" && break; sleep 0.1; done
rm -f "$TMP/ran"
guarded -- touch "$TMP/ran"
check "lock: second instance -> exit 5" eq "$RC" 5
check "lock: second command not run" test ! -e "$TMP/ran"
check "lock: message names holder" has "$ERR" "\"pid\":$FIRST,"
check "lock: one JSON line pid|profile|log dir|cmd" eq "$(lock_json)" "$FIRST|exclusive|$TMP/logs|${WANT_CMD% }"
check "lock: file rewritten in place (same inode)" eq "$(stat -f %i "$TMP/lock")" "$INODE"
wait "$FIRST"
check "lock: first instance finished ok" eq "$?" 0

# lock: concurrent start, exactly one wins
for i in 1 2 3 4 5 6; do
  ("${TO[@]}" "$GUARD" -- sleep 1 >/dev/null 2>&1; echo $? > "$TMP/race.$i") &
done
wait
check "lock: 6 concurrent guards -> exactly one runs" eq "$(cat "$TMP"/race.* | sort | tr '\n' ' ')" "0 5 5 5 5 5 "

# lock: guard SIGKILLed while its child lives -> lock stays held by the child
"${TO[@]}" "$GUARD" -- sleep 45 2>/dev/null &
PID=$!
sleep 1
kill -KILL "$PID"
wait "$PID" 2>/dev/null
guarded -- true
check "lock: guard SIGKILLed, child alive -> exit 5" eq "$RC" 5
pkill -f "sleep 45"
sleep 0.5
check "lock: free once that child is gone" lock_free

# --- watchdog: swap growth / critical pressure mid-run
ramp swap 100 1125
START=$SECONDS
guarded -- sleep 41
check "watchdog swap +1025 MiB -> exit 4" eq "$RC" 4
check "watchdog swap: stopped quickly" test $((SECONDS - START)) -lt 8
check "watchdog swap: child gone" gone "sleep 41"
check "watchdog swap: message" has "$ERR" "swap_growth_mb=1025"
check "watchdog swap: logged" has "$(cat "$(latest_log)")" "watchdog_kill swap_growth_mb=1025"

ramp swap 100 1124
guarded -- sleep 4
check "watchdog swap +1024 MiB (not more) -> runs to end" eq "$RC" 0

defaults; ramp level 1 4
guarded -- sleep 42
check "watchdog pressure critical -> exit 4" eq "$RC" 4
check "watchdog pressure: child gone" gone "sleep 42"

# child (and its whole group) ignores SIGTERM -> SIGKILL after grace
defaults; ramp swap 100 2000
START=$SECONDS
guarded -- sh -c 'trap "" TERM; sleep 43; sleep 43'
check "watchdog SIGKILL escalation -> exit 4" eq "$RC" 4
check "watchdog SIGKILL: waited for grace" test $((SECONDS - START)) -ge 3
check "watchdog SIGKILL: group gone" gone "sleep 43"
check "watchdog SIGKILL: logged" has "$(cat "$(latest_log)")" "sigkill"
defaults

# --- guard itself gets a signal: child group stopped, lock released, 128+n
SIGS="TERM HUP ALRM USR1 PIPE"
# a shell started with SIGPIPE ignored (GitHub Actions does that) cannot trap it, so that case is not testable there
[ "$(perl -e 'print $SIG{PIPE} // q()')" = IGNORE ] && SIGS="TERM HUP ALRM USR1"
for sig in $SIGS; do
  "${TO[@]}" "$GUARD" -- sh -c 'sleep 44; true' 2>/dev/null &
  PID=$!
  sleep 1
  kill -"$sig" "$PID"
  wait "$PID"
  RC=$? WANT=$((128 + $(kill -l "$sig")))
  check "guard SIG$sig -> exit $WANT" eq "$RC" "$WANT"
  check "guard SIG$sig: child gone" gone "sleep 44"
  check "guard SIG$sig: lock released" lock_free
done

# --- interactive: child owns the terminal foreground and can read from it
OUT=$( (sleep 1; printf 'typed\r'; sleep 2) |
  "${TO[@]}" script -q /dev/null "$GUARD" -- sh -c 'read x; echo "got:$x"' 2>&1 | tr -d '\r')
check "tty: child reads terminal input" has "$OUT" "got:typed"

# Ctrl-Z must not stop the child while the guard waits for it
OUT=$( (sleep 1; printf '\032'; sleep 3) |
  "${TO[@]}" script -q /dev/null "$GUARD" -- perl -e 'sleep 2; print "child-done\n"' 2>&1 | tr -d '\r')
check "tty: Ctrl-Z ignored, child completes" has "$OUT" "child-done"

# guard as background job of an interactive shell must not steal the terminal
OUT=$( (sleep 1; printf '%s -- sleep 2 &\r' "$GUARD"; sleep 4; printf 'echo alive-$((40 + 2))\r'; sleep 1; printf 'exit\r') |
  "${TO[@]}" script -q /dev/null bash --norc --noprofile -i 2>&1 | tr -d '\r')
check "tty: background guard leaves the shell usable" has "$OUT" "alive-42"

# --- smoke: real tools, real lock, real model (micro, random weights); runs > 2 s so the
# watchdog samples real probes at least once (interval and log period stay 1 s)
if [ "${1:-}" != --no-smoke ]; then
  MODEL="${BYTEPLAN_MODELS:-$HOME/byteplan-models}/micro/micro-qwen4exp-realqsa.gguf"
  PATH=$REAL_PATH
  unset BYTEPLAN_GUARD_LOCK BYTEPLAN_GUARD_LOG_DIR
  guarded --profile parallel -- \
    "$ROOT/vendor/build-oracle/bin/llama-bench" -m "$MODEL" -p 16 -n 128 -r 8 -o jsonl </dev/null
  sed 's/^/     /' "$TMP/err" | grep 'run-guarded:'
  check "smoke: llama-bench micro under real preflight -> exit 0" eq "$RC" 0
  TS=$(echo "$OUT" | sed -nE 's/.*"avg_ts": *([0-9.]+).*/\1/p' | tr '\n' ' ')
  check "smoke: pp and tg t/s > 0 ($TS)" awk -v ts="$TS" 'BEGIN { n = split(ts, a, " "); for (i = 1; i <= n; i++) if (a[i] <= 0) exit 1; exit n != 2 }'
  SMOKE_LOG=$(echo "$ERR" | sed -n 's/^run-guarded: Log: //p')
  check "smoke: log in logs/guard/" has "$SMOKE_LOG" "$ROOT/logs/guard/"
  check "smoke: watchdog sampled real probes (>= 2 samples)" test "$(grep -c ' sample swap_used_mb=[0-9]' "$SMOKE_LOG")" -ge 2
  check "smoke: real lock released" lock_free "$HOME/.cache/byteplan/model.lock"
fi

echo "$PASS passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
