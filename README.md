<div align="center">

<h1>terminal-tetris</h1>

<p><strong>A complete Tetris game for the Ubuntu terminal, written in C with ncurses.</strong></p>

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="tetris.c"><img src="https://img.shields.io/badge/C-C99-00599C.svg?logo=c&logoColor=white" alt="Written in C99"></a>
  <img src="https://img.shields.io/badge/TUI-ncurses-3A7D44.svg?logo=gnu&logoColor=white" alt="Runs on ncurses">
  <img src="https://img.shields.io/badge/platform-Ubuntu%20%7C%20Debian-E95420.svg?logo=ubuntu&logoColor=white" alt="Platform: Ubuntu and Debian">
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

## Requirements

Ubuntu / Debian, and the ncurses development headers:

```sh
sudo apt update && sudo apt install -y build-essential libncurses-dev
```

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

Gravity ramps from 800 ms per step down to a floor of 80 ms, and the level rises
every 10 lines, except in Expert which starts partway up that curve.

Sprint ranks by **fastest time**, not highest score — its leaderboard shows a
`TIME` column instead of `SCORE`. A time is only recorded if you actually clear
all 40 lines; bailing out at 30 does not post an unbeatable short time. The HUD
swaps the level readout for a clock in any mode with an objective, counting up
in Sprint and down in Ultra.

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
needs a pty. `tests/run_tests.sh` sets one up, builds the game, and runs three
suites against it:

```sh
tests/run_tests.sh
```

It covers all four mode HUDs, drop scoring, pause, the terminal-size gate,
score-file parsing, and both end conditions end-to-end (Ultra timing out to
`TIME UP`, Sprint reaching `CLEARED` with a time on the board). Everything it
builds goes to `$TETRIS_WORK` (default `/tmp/terminal-tetris-test`), so your
working tree is left alone — the run finishes by verifying that.

Needs `python3` with `venv`. `pyte` is installed into a venv for you.

The end conditions that would otherwise take minutes to reach are exercised via
variants built on the fly with a shortened constant — a 3-second Ultra clock, a
one-line Sprint goal. Same code path, different numbers.

## Layout

```
tetris.c      the entire game
LICENSE       the MIT license
tests/        pty test suite and its runner
CLAUDE.md     project memory and conventions
README.md     this file
```

## License

MIT — see [LICENSE](LICENSE). Do whatever you like with it.
