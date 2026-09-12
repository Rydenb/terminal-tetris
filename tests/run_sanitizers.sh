#!/usr/bin/env bash
# Rebuild the game and its shortened-constant variants under AddressSanitizer and
# UndefinedBehaviorSanitizer, then drive the pty suites against those builds.
#
#   tests/run_sanitizers.sh
#
# This reuses the scratch directory that tests/run_tests.sh sets up, so run that
# first -- it is what generates the variant sources and the ncurses prefix. CI
# runs the two in order. It stays separate from run_tests.sh because an
# instrumented build is much slower and is not the thing that ships.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${1:-$HERE/../tetris.c}"
WORK="${TETRIS_WORK:-/tmp/tetrisplus-test}"
export TETRIS_WORK="$WORK"

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

INC="$WORK/root/usr/include"
LIB="$WORK/root/usr/lib/x86_64-linux-gnu"
PY="$WORK/venv/bin/python"

# Everything below is produced by run_tests.sh. Say so plainly rather than
# failing three steps later with a confusing gcc error.
if [ ! -f "$INC/ncurses.h" ] || [ ! -x "$PY" ] \
   || [ ! -f "$WORK/tetris-narrow.c" ] || [ ! -f "$WORK/tetris-ultra-short.c" ]; then
    echo "run_sanitizers.sh: $WORK is not set up yet."
    echo "Run tests/run_tests.sh first -- it generates the variants and the venv."
    exit 1
fi

# -O1 keeps the build quick while still giving the sanitizers enough
# line information to be useful; -fno-omit-frame-pointer makes stacks readable.
FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g -O1"

say "rebuilding with ASan + UBSan"
gcc $FLAGS -Wall -Wextra "$SRC"                     -o "$WORK/tetris"            -I"$INC" -L"$LIB" -lncurses -ltinfo
gcc $FLAGS -Wall -Wextra "$WORK/tetris-narrow.c"    -o "$WORK/tetris-narrow"     -I"$INC" -L"$LIB" -lncurses -ltinfo
gcc $FLAGS -Wall -Wextra "$WORK/tetris-ultra-short.c" -o "$WORK/tetris-ultra-short" -I"$INC" -L"$LIB" -lncurses -ltinfo
echo "   three instrumented binaries built"

# If the runtime did not actually attach, every run below would pass for the
# wrong reason. Check, so a green result here means something.
if ! ldd "$WORK/tetris" | grep -q libasan; then
    echo "   ERROR: libasan is not linked -- the sanitizers would be a no-op"
    exit 1
fi

# Leak reports are off on purpose: ncurses holds allocations until endwin, so
# the exit report is noise for a curses program. Memory *errors* -- overflow,
# use-after-free, UB -- are what this job exists to catch.
export ASAN_OPTIONS="${ASAN_OPTIONS:-detect_leaks=0:abort_on_error=0}"

rc=0
for suite in test_all.py test_timeup.py test_cleared.py; do
    say "$suite (instrumented)"
    (cd "$HERE" && "$PY" "$HERE/$suite") || rc=1
done

say "sanitizer result"
if [ $rc -eq 0 ]; then
    echo "   NO SANITIZER ERRORS"
else
    echo "   FAILURES -- see above"
fi
exit $rc
