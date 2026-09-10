# terminal-tetris

A complete Tetris game for the Ubuntu terminal, written in C with ncurses.

Single file, no build system, no dependencies beyond libncurses. Comes with a
game menu, a persistent arcade-style high score table, and a game mode system
that is ready for more variants.

```
┌──────────────────────────────────────────────────────────────┐
│                          T E T R I S                         │
│                    ──────────────────────────                │
│                                                              │
│                      Mode    <  Marathon  >                  │
│       Classic endless tetris. Clear lines, survive, score.   │
│                                                              │
│                    ──────────────────────────                │
│                                                              │
│                         > Play                               │
│                           High Scores                        │
│                           Quit                               │
│                                                              │
│         Up/Dn move    L/R mode    Enter select    Q quit     │
└──────────────────────────────────────────────────────────────┘
```

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
| `Q`             | Quit to the shell                     |

### Game over

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

| Mode     | Description                                                |
| -------- | ---------------------------------------------------------- |
| Marathon | Classic endless tetris. Level rises every 10 lines; gravity ramps from 800 ms per step down to a floor of 80 ms. |

More modes are planned. Adding one is a single row in the `MODES[]` table at
the top of `tetris.c` — the rules engine, the menu and the score tables all read
their behaviour from there. Each mode keeps its own high score table.

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
# <mode> <initials> <score> <level> <lines> <date>
marathon SUO 12400 5 42 2026-09-09
```

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

## Layout

```
tetris.c      the entire game
CLAUDE.md     project memory and conventions
README.md     this file
```

## License

None declared yet. Add a `LICENSE` file if you want to make the terms explicit.
