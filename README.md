<div align="center">

<h1>terminal-tetris</h1>

<p><strong>A complete Tetris game for your terminal, written in C with ncurses.</strong></p>

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="tetris.c"><img src="https://img.shields.io/badge/C-C99-00599C.svg?logo=c&logoColor=white" alt="Written in C99"></a>
  <img src="https://img.shields.io/badge/TUI-ncurses-3A7D44.svg?logo=gnu&logoColor=white" alt="Runs on ncurses">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20BSD-2C2D72.svg" alt="Platform: Linux, macOS and BSD">
  <img src="https://img.shields.io/badge/packaging-.deb-A80030.svg?logo=debian&logoColor=white" alt="Ships a Debian package">
</p>

</div>

Single file, no build system, no dependencies beyond libncurses. Comes with a
game menu, a persistent arcade-style high score table, and a game mode system
that is ready for more variants.

**The menu** — pick a mode with Left/Right, pick an action with Up/Down:

```
                    T E T R I S
           ──────────────────────────────

               Mode    <  Marathon  >
 Classic endless tetris. Clear lines, survive, score.

           ──────────────────────────────

                > Play

                  High Scores

                  Quit

  Up/Dn move    L/R mode    Enter select    Q quit
```

**Marathon, mid-game** — the falling piece, the ghost showing where a hard drop
lands, the next-piece preview, and the live counters:

```
┌────────────────────┐  TETRIS
│. . . . . []. . . . │  ──────────────
│. . . [][][]. . . . │
│. . . . . . . . . . │  Score
│. . . . . . . . . . │  164
│. . . . . . . . . . │
│. . . . . . . . . . │  Level
│. . . . . . . . . . │  1
│. . . . . . . . . . │
│. . . . . . . . . . │  Lines
│. . . . . . . . . . │  0
│. . . . . . . . . . │
│. . . . . . . . . . │  Next
│. . . . . . . . . . │  . [][]
│. . . . . . . . . . │  [][].
│. . . . . []. . . . │  L/R   move
│. . . [][][]. . . . │  Up    rotate
│[][][][][][]. . . . │  Dn    soft drop
│[][]. . . []. . . . │  Space hard drop
│[][]. . . [][][][]. │  P     pause
│. [][]. . . . [][][]│  M     menu
└────────────────────┘  Q     quit
```

That lone `[]` a few rows above the stack is the **ghost** — it marks where the
piece lands if you hit Space. It renders dimmed in a real terminal.

## Install

All three routes end the same way: `tetris` works from any directory.

### From a release

Download the `.deb` from the
[latest release](https://github.com/aacanadaa/terminal-tetris/releases/latest)
and install it. The glob saves you typing the version:

```sh
sudo apt install ./terminal-tetris_*_amd64.deb
```

That is the one to hand to somebody else. It puts `tetris` in `/usr/bin` for
every user on the machine, pulls in `libncurses6` automatically, and installs a
man page, so `man tetris` works. Remove it with
`sudo apt remove terminal-tetris`.

### From a clone, on this machine

```sh
./install.sh
```

That builds the game and installs it to `/usr/local/bin/tetris`, asking for
sudo only if that directory is not writable by you. To keep it out of the
system entirely:

```sh
./install.sh --user     # installs to ~/.local/bin, never uses sudo
```

The installer checks for a compiler and the ncurses headers before it starts,
and prints the exact `apt` line if either is missing.

### Building the package yourself

```sh
./build-deb.sh              # -> dist/terminal-tetris_<version>_<arch>.deb
sudo apt install ./dist/terminal-tetris_*_amd64.deb
```

### Uninstall

Match the flags you installed with. The prefix has to line up, or the script
looks in the wrong place and finds nothing:

| How you installed it                        | How to undo it                    |
| ------------------------------------------- | --------------------------------- |
| `sudo apt install ./terminal-tetris_*.deb`  | `sudo apt remove terminal-tetris` |
| `./install.sh` (system-wide)                | `./install.sh --uninstall`        |
| `./install.sh --user`                       | `./install.sh --user --uninstall` |

The two script forms need the clone to still be on disk. If you have since
deleted it, the install is only a single file:

```sh
rm ~/.local/bin/tetris           # --user install
sudo rm /usr/local/bin/tetris    # system-wide install
```

**Your high scores are not part of the install**, so none of the above removes
them — they live outside the repo and survive a reinstall. To wipe those too:

```sh
rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/terminal-tetris"
```

And none of it is a Makefile: this project deliberately does not have one.

## Requirements

Only needed to build from source — the installers handle the rest.

The game is POSIX C99 and needs nothing beyond ncurses. It builds clean under
`-std=c99 -D_POSIX_C_SOURCE=200809L` with no GNU or glibc extensions, and uses
only long-standing ncurses calls (`initscr`, `use_default_colors`, `napms` and
the basics), so it is not tied to one library version or one flavour of Unix.

- **Ubuntu / Debian** — `sudo apt install -y build-essential libncurses-dev`
- **macOS** — `xcode-select --install`; ncurses ships with the system
- **FreeBSD / OpenBSD / NetBSD** — ncurses is in the base system, so there is
  nothing to install

Then build it as shown below.

> Developed and tested on Linux. The other platforms are expected to work — the
> source is pure POSIX and the curses calls are all baseline — but they are not
> covered by the test suite, which drives a real pty.

## Build

```sh
gcc tetris.c -o tetris -lncurses
```

## Run

```sh
./tetris
```

Your terminal needs to be at least **50 columns x 22 rows**. Most default
80x24 terminal windows are fine. Resize at any time — the board and menus
recentre themselves.

## The menu

The game opens on the menu. Up/Down picks an action, Left/Right switches game
mode, Enter confirms.

- **Play** — start a game (or play again after a game over)
- **High Scores** — the top 10 for the current mode
- **Quit** — leave, restoring your terminal

## Controls

### In the menu

| Key             | Action                                |
| --------------- | ------------------------------------- |
| `Up` / `Down`   | Move between actions                  |
| `Left` / `Right`| Switch game mode                      |
| `Enter`         | Confirm                               |
| `Q`             | Quit                                  |

### In a game

| Key             | Action                                |
| --------------- | ------------------------------------- |
| `Left` / `Right`| Move the piece sideways               |
| `Up`            | Rotate clockwise                      |
| `Down`          | Soft drop (+1 point per cell)         |
| `Space`         | Hard drop (+2 points per cell)        |
| `P`             | Pause / resume                        |
| `M`             | Back to the main menu (abandons the run) |
| `Q`             | Quit to the shell                     |

### When the run ends

A run ends when you top out, or when the mode's objective is met — the panel
reads `GAME OVER`, `CLEARED` or `TIME UP` accordingly.

| Key             | Action                                |
| --------------- | ------------------------------------- |
| `R`             | Play again, same mode                 |
| `M`             | Back to the main menu                 |
| `Q`             | Quit                                  |

### Entering your initials

If your score makes the top 10, you get an arcade-style prompt:

| Key             | Action                                |
| --------------- | ------------------------------------- |
| `A`-`Z`, `0`-`9`| Type into the current slot            |
| `Backspace`     | Delete the previous character         |
| `Enter`         | Save the score                        |
| `Esc`           | Skip — the score is not saved         |

## Game modes

| Mode         | Objective                                                   | Ranked by |
| ------------ | ----------------------------------------------------------- | --------- |
| **Marathon** | Endless. Survive and score.                                 | Score     |
| **Sprint**   | Clear 40 lines as fast as you can.                          | **Time**  |
| **Ultra**    | Two minutes on the clock. Score as much as you can.         | Score     |
| **Expert**   | Endless, but starts at level 10 — gravity opens at 170 ms per step instead of 800. | Score |
| **Dig**      | Start on 10 rows of garbage, one gap each. Dig them all out as fast as you can. | **Time** |

Gravity ramps from 800 ms per step down to a floor of 80 ms, and the level rises
every 10 lines, except in Expert which starts partway up that curve.

Sprint and Dig rank by **fastest time**, not highest score — their leaderboards
show a `TIME` column instead of `SCORE`. A time is only recorded if you actually
finish; bailing out at 30 lines does not post an unbeatable short time. The HUD
swaps the level readout for a clock in any mode with an objective, counting up
in Sprint and Dig and down in Ultra.

In Dig the garbage is drawn as `##`, and no gap sits directly under the one
above it, so you cannot drain the pile down a single well. The HUD counts the
garbage rows left instead of lines: a line cleared above the garbage does not
bring you any closer.

Adding a mode is a single row in the `MODES[]` table at the top of `tetris.c` —
the rules engine, the menu, the HUD and the score tables all read their
behaviour from there. Each mode keeps its own high score table.

## High scores

Scores persist between sessions, in the standard location for application data:

```
$XDG_DATA_HOME/terminal-tetris/scores
# or, if XDG_DATA_HOME is unset:
~/.local/share/terminal-tetris/scores
```

The file is plain text so you can read or back it up easily:

```
# terminal-tetris high scores
# <mode> <initials> <score> <level> <lines> <date> [<elapsed_ms>]
marathon SUO 12400 5 42 2026-09-09 0
sprint BOT 13782 5 40 2026-09-09 13061
```

The trailing time field is optional and only meaningful for time-ranked modes —
files written before Sprint existed load fine without it, and rows lacking a
time simply sort last on a time-ranked board.

Only the top 10 are kept per mode. The loader is deliberately forgiving: it
ignores comments, blank lines, malformed rows, and rows for modes that no longer
exist. Initials are forced to three display-safe characters, so hand-editing can
never inject terminal escape sequences into the UI.

**To wipe your scores**, just delete the file:

```sh
rm ~/.local/share/terminal-tetris/scores
```

If the file cannot be read or written for any reason, the game still plays —
only the score table is lost.

## Scoring

| Lines cleared at once | Points          |
| --------------------- | --------------- |
| 1                     | 100 x level     |
| 2                     | 300 x level     |
| 3                     | 500 x level     |
| 4 (a "tetris")        | 800 x level     |

Soft dropping adds 1 point per cell; hard dropping adds 2.

## Features

- All seven tetrominoes (I, J, L, O, S, T, Z), each in its own colour
- Wall kicks, so rotations work flush against the walls
- A ghost piece showing where a hard drop will land
- A 7-bag randomiser, so you never go long stretches without an I piece
- Next-piece preview, score, level and line counters
- Persistent per-mode top-10 high scores with arcade initials
- A menu and a leaderboard screen
- Non-blocking input on a fixed ~60 fps loop, so gravity is smooth and
  independent of your keypresses
- The terminal is always restored on exit, including on Ctrl-C

## Testing

The game is a full-screen TUI, so it can't be exercised in a plain shell — it
needs a pty. `tests/run_tests.sh` sets one up, builds the game, and runs four
suites against it:

```sh
tests/run_tests.sh
```

It covers all five mode HUDs, drop scoring, pause, the terminal-size gate,
score-file parsing, and every end condition end-to-end (Ultra timing out to
`TIME UP`, Sprint and Dig reaching `CLEARED` with a time on the board). Everything it
builds goes to `$TETRIS_WORK` (default `/tmp/terminal-tetris-test`), so your
working tree is left alone — the run finishes by verifying that.

Needs `python3` with `venv`. `pyte` is installed into a venv for you.

The end conditions that would otherwise take minutes to reach are exercised via
variants built on the fly with a shortened constant — a 3-second Ultra clock, a
one-line Sprint goal, a single row of Dig garbage. Same code path, different numbers.

## Layout

```
tetris.c      the entire game
install.sh    build and install it as `tetris`
build-deb.sh  package it as a .deb
packaging/    the man page
LICENSE       the MIT license
tests/        pty test suite and its runner
CLAUDE.md     project memory and conventions
README.md     this file
```

## License

MIT — see [LICENSE](LICENSE). Do whatever you like with it.
