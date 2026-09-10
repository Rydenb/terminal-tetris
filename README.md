# terminal-tetris

A complete Tetris game for the Ubuntu terminal, written in C with ncurses.

Single file, no build system, no dependencies beyond libncurses.

```
┌──────────────────────┐  TETRIS
│                      │  ──────────────
│                      │  Score
│           []         │    1200
│         [][]         │  Level
│  []     []           │    2
│  [][]   []           │  Lines
│  []     []           │    14
│  [][] [][][]  [][]   │  Next
│  [][] [][][]  [][]   │  []
│  [][] [][][] [][] [] │  []  []
│                      │
│                      │  L/R   move
│                      │  Up    rotate
│                      │  Dn    soft drop
│                      │  Space hard drop
│                      │  P     pause
└──────────────────────┘  Q     quit
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

Your terminal needs to be at least **38 columns x 22 rows**. Most default
80x24 terminal windows are fine. Resize at any time — the board recentres
itself.

## Controls

| Key             | Action                                |
| --------------- | ------------------------------------- |
| `Left` / `Right`| Move the piece sideways               |
| `Up`            | Rotate clockwise                      |
| `Down`          | Soft drop (+1 point per cell)         |
| `Space`         | Hard drop (+2 points per cell)        |
| `P`             | Pause / resume                        |
| `Q`             | Quit                                  |
| `R`             | Restart (on the game over screen)     |

## Scoring

| Lines cleared at once | Points          |
| --------------------- | --------------- |
| 1                     | 100 x level     |
| 2                     | 300 x level     |
| 3                     | 500 x level     |
| 4 (a "tetris")        | 800 x level     |

The level rises every 10 lines, and the piece falls faster with each level —
from a lazy 800 ms per step at level 1 down to a floor of 80 ms.

## Features

- All seven tetrominoes (I, J, L, O, S, T, Z), each in its own colour
- Wall kicks, so rotations work flush against the walls
- A ghost piece showing where a hard drop will land
- A 7-bag randomiser, so you never go long stretches without an I piece
- Next-piece preview, score, level and line counters
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
