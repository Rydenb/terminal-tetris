# CLAUDE.md — terminal-tetris

Project memory for Claude Code. Read this before changing anything here.

## Project

A complete Tetris game for the Ubuntu terminal, written in C against ncurses.
Deliberately a **single translation unit** — no Makefile, no headers, no
subdirectories. Everything lives in `tetris.c`.

## Build

```sh
gcc tetris.c -o tetris -lncurses
```

System dependency (Ubuntu/Debian):

```sh
sudo apt update && sudo apt install -y build-essential libncurses-dev
```

There is no Makefile on purpose. If you find yourself wanting one, the change
is out of scope for this project.

## Run

```sh
./tetris
```

Needs a terminal of at least **38 columns x 22 rows**. The game prints a
"Terminal too small" notice instead of drawing garbage if it is smaller.

## Code style rules

- **Single-file ANSI C.** All code stays in `tetris.c`. Do not split it up.
- **4-space indentation.** No tabs.
- C99 declarations. Where a variable is only used in a narrow scope, declare it
  there rather than at the top of the function.
- **Explicit ncurses cleanup on every exit path.** `endwin()` must run whether
  the player quits, dies, or hits Ctrl-C. This is enforced two ways:
  `atexit(cleanup)` as the backstop, and a `SIGINT`/`SIGTERM` handler that sets
  `g_quit` so the main loop unwinds normally.
- Section banners (`/* ---- name */`) separate setup, rules, drawing, and main.
- Keep comments about *why*, not *what*. The rotation derivation and the
  line-clear compaction both deserve their existing notes; trivia does not.

## Architecture notes

- `SHAPE_SRC` holds only the **spawn orientation** of each tetromino. The other
  three rotations are generated at start-up in `init_shapes()` by rotating the
  4x4 box a quarter turn. Never hand-write rotation tables.
- The board stores `0` for empty and `piece + 1` for a settled cell, so the
  stored value *is* the ncurses colour-pair index. That coupling is intentional.
- The main loop is non-blocking: `nodelay(stdscr, TRUE)`, drain all pending
  keypresses, then compare `CLOCK_MONOTONIC` against `last_drop` to decide
  whether gravity fires. Gravity is therefore independent of the redraw rate and
  of how long the player holds a key.
- `compute_layout()` runs every frame, so terminal resizes are picked up for
  free — no `SIGWINCH` handling needed.

## Testing

Compiles clean with `-Wall -Wextra`. Please keep it that way:

```sh
gcc -Wall -Wextra tetris.c -o tetris -lncurses
```

There is no automated test suite; the game is verified by playing it. If you
touch collision, rotation, or line clearing, check these by hand:

- Rotating a piece flush against each of the four walls (wall kicks).
- Rotating the I piece and the O piece in a tight well.
- Clearing a single line, and a tetris (four rows) at once.
- Filling the stack to the top and confirming the game-over overlay appears and
  that the terminal is restored cleanly on `Q`.

## Git

Default branch is `main`. Do not commit the `tetris` binary — it is in
`.gitignore` and always will be.
