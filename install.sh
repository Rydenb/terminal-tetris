#!/bin/sh
#
# install.sh -- build tetrisplus and put `tetrisplus` on your PATH.
#
#   ./install.sh                install to /usr/local/bin (sudo if needed)
#   ./install.sh --user         install to ~/.local/bin, never needs sudo
#   ./install.sh --prefix DIR   install to DIR/bin
#   ./install.sh --uninstall    remove an installed `tetrisplus`
#
# This project deliberately has no Makefile (see CLAUDE.md), so installation
# lives here rather than in a `make install` target.

set -eu

PROG=tetrisplus
SRC_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SRC=$SRC_DIR/tetris.c

# -std=c99 is deliberately absent. tetris.c calls clock_gettime() and uses
# struct timespec, which glibc only declares when the POSIX feature macros are
# in scope; strict ISO C99 hides them and the build fails. Do not add it.
CC=${CC:-gcc}
CFLAGS=${CFLAGS:--O2 -Wall -Wextra}

prefix=/usr/local
do_uninstall=0

say() { printf '%s\n' "$*"; }
die() { printf 'install.sh: %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<EOF
Usage: ./install.sh [--user] [--prefix DIR] [--uninstall]

Builds the game and installs it as "$PROG", so you can run it from any
directory.

  (no options)    install to /usr/local/bin, using sudo if that directory is
                  not writable by you
  --user          install to ~/.local/bin; never uses sudo
  --prefix DIR    install to DIR/bin
  --uninstall     remove an installed $PROG
  -h, --help      show this message and exit

Environment:
  CC              C compiler to use      (default: gcc)
  CFLAGS          compiler flags         (default: -O2 -Wall -Wextra)
EOF
}

while [ $# -gt 0 ]; do
    case $1 in
        --user)      prefix=$HOME/.local ;;
        --prefix)    [ $# -ge 2 ] || die "--prefix needs a directory"
                     prefix=$2; shift ;;
        --prefix=*)  prefix=${1#*=} ;;
        --uninstall) do_uninstall=1 ;;
        -h|--help)   usage; exit 0 ;;
        *)           usage >&2; die "unknown option: $1" ;;
    esac
    shift
done

bindir=$prefix/bin
dest=$bindir/$PROG

# Walk up to the nearest directory that exists and see whether we could create
# $bindir inside it. For the default /usr/local/bin this is false for a normal
# user, which is what turns on sudo.
writable() {
    d=$1
    while [ ! -d "$d" ]; do
        parent=$(dirname -- "$d")
        [ "$parent" = "$d" ] && break
        d=$parent
    done
    [ -w "$d" ]
}

SUDO=
if [ "$(id -u)" -ne 0 ] && ! writable "$bindir"; then
    command -v sudo >/dev/null 2>&1 || die \
        "$bindir is not writable and sudo is not installed.
Re-run with --user to install into your home directory instead."
    SUDO=sudo
fi

# $SUDO is intentionally unquoted: when empty it expands to nothing, so the
# command runs directly rather than trying to exec "".
as_root() {
    if [ -n "$SUDO" ]; then $SUDO "$@"; else "$@"; fi
}

if [ "$do_uninstall" -eq 1 ]; then
    if [ ! -e "$dest" ]; then
        say "Nothing to remove: $dest does not exist."
        say "If you installed with --user, try: ./install.sh --user --uninstall"
        exit 0
    fi
    as_root rm -f "$dest"
    say "Removed $dest"
    say "Your high scores were left in place (they live under \$XDG_DATA_HOME)."
    exit 0
fi

# --- preflight -------------------------------------------------------------

[ -f "$SRC" ] || die "cannot find tetris.c next to this script (looked in $SRC_DIR)"

# The game is portable, so the installer has to be too. Printing a Debian `apt`
# line at a macOS user is worse than printing nothing, so branch on the platform
# before falling back to sniffing /etc/os-release.
os_id() {
    [ -r /etc/os-release ] || return 0
    ( . /etc/os-release 2>/dev/null || exit 0; printf '%s %s' "${ID:-}" "${ID_LIKE:-}" )
}

toolchain_hint() {
    case $(uname -s 2>/dev/null) in
        Darwin)
            printf '  xcode-select --install\n'
            return ;;
        FreeBSD)
            printf '  pkg install gcc ncurses\n'
            return ;;
        OpenBSD|NetBSD|DragonFly)
            printf '  # ncurses is in the base system; install a C compiler\n'
            return ;;
    esac

    case " $(os_id) " in
        *debian*|*ubuntu*) printf '  sudo apt update && sudo apt install -y build-essential libncurses-dev\n' ;;
        *fedora*|*rhel*)   printf '  sudo dnf install -y gcc ncurses-devel\n' ;;
        *arch*)            printf '  sudo pacman -S --needed base-devel ncurses\n' ;;
        *suse*)            printf '  sudo zypper install -y gcc ncurses-devel\n' ;;
        *alpine*)          printf '  sudo apk add build-base ncurses-dev\n' ;;
        *)                 printf '  install a C compiler and the ncurses development headers\n' ;;
    esac
}

command -v "$CC" >/dev/null 2>&1 || die "no C compiler found ($CC). Install the toolchain with:
$(toolchain_hint)"

# On macOS $CC exists as a stub that fails until the Xcode command line tools
# are installed, so run it rather than trusting PATH -- otherwise the ncurses
# check below reports missing headers and sends you chasing the wrong problem.
if ! printf 'int main(void){return 0;}\n' | "$CC" -x c -fsyntax-only - >/dev/null 2>&1; then
    die "the C compiler ($CC) is present but does not work. Install the toolchain with:
$(toolchain_hint)"
fi

if ! printf '#include <ncurses.h>\n' | "$CC" -x c -fsyntax-only - >/dev/null 2>&1; then
    die "the ncurses headers are missing. Install them with:
$(toolchain_hint)"
fi

# --- build -----------------------------------------------------------------

build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM

say "Building $PROG with $CC $CFLAGS"
# shellcheck disable=SC2086  # $CFLAGS is a flag list and must word-split.
"$CC" $CFLAGS -o "$build_dir/$PROG" "$SRC" -lncurses ||
    die "the build failed (see the compiler output above)"

# --- install ---------------------------------------------------------------

as_root install -d -m 0755 "$bindir"
as_root install -m 0755 "$build_dir/$PROG" "$dest"

say ""
say "Installed $dest"

# Warn about the two ways a fresh install can still appear broken: the
# directory is not on PATH at all, or an older copy shadows it.
case ":${PATH}:" in
    *":$bindir:"*)
        found=$(command -v "$PROG" 2>/dev/null || true)
        if [ -n "$found" ] && [ "$found" != "$dest" ]; then
            say ""
            say "NOTE: '$PROG' currently resolves to $found, which is not the"
            say "copy just installed. Something earlier on your PATH is"
            say "shadowing it."
        fi
        say "Run it by typing: $PROG"
        ;;
    *)
        say ""
        say "NOTE: $bindir is not on your PATH, so typing '$PROG' will not"
        say "find it yet. Add this to ~/.bashrc (or ~/.profile) and reopen"
        say "your terminal:"
        say ""
        say "  export PATH=\"$bindir:\$PATH\""
        ;;
esac
