# CLAUDE.md — terminal-tetris

Project memory for Claude Code. Read this before changing anything here.

## Project

A complete Tetris game for the Ubuntu terminal, written in C against ncurses.
Deliberately a **single translation unit** — no Makefile, no headers, no
subdirectories. Everything lives in `tetris.c`, currently ~1100 lines.

Features: a game menu, a mode system, and a persistent per-mode arcade high
score table.

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

**Note on linking:** the plain `-lncurses` form is correct once
`libncurses-dev` is installed. If you are building against headers extracted
into a userspace prefix (see *Building without root* below), you must also pass
`-ltinfo` explicitly, because `cbreak` and friends live in libtinfo.

### Building without root

`sudo` in this environment needs an interactive password. To build anyway:

```sh
apt-get download libncurses-dev && dpkg -x libncurses-dev_*.deb root/
gcc tetris.c -o tetris -Iroot/usr/include -L<dir-with-libncurses.so> \
    -lncurses -ltinfo
```

The runtime `libncurses.so.6` is usually already present; only the headers and
the `.so` dev symlink are missing.

## Run

```sh
./tetris
```

Needs a terminal of at least **50 columns x 22 rows**. The menu footer and the
leaderboard columns are what set the 50; the board alone would fit in 38. Any
screen that is too small shows a "Terminal too small" notice rather than drawing
garbage.

## Code style rules

- **Single-file ANSI C.** All code stays in `tetris.c`. Do not split it up.
- **4-space indentation.** No tabs.
- C99 declarations. Where a variable is only used in a narrow scope, declare it
  there rather than at the top of the function.
- **Explicit ncurses cleanup on every exit path.** `endwin()` must run whether
  the player quits, dies, or hits Ctrl-C. Enforced two ways: `atexit(cleanup)`
  as the backstop, and a `SIGINT`/`SIGTERM` handler that sets `g_quit` so the
  main loop unwinds normally.
- Section banners (`/* ---- name */`) separate setup, rules, scores, drawing,
  screens, and main.
- Keep comments about *why*, not *what*. The rotation derivation, the
  line-clear compaction, the shared-edge table alignment and the initials
  sanitiser all deserve their existing notes; trivia does not.

## Architecture

### Game modes

`MODES[]` near the top is the single source of truth for mode behaviour — name,
blurb, starting level, lines-per-level, the gravity curve, and any objective
(`goal_lines`, `time_limit_sec`) or ranking rule (`rank_by_time`). There are **no
hard-coded 800 / 70 / 80 / 10 / 40 / 120 constants anywhere else in the file**;
the engine reads them off `Game::mode`. Adding a mode is one row in that table
plus a `blurb`.

The id string is the stable key used in the score file, so **never change an
existing id** — doing so orphans everyone's saved scores.

`mode_is_timed()` really means "has an objective"; the HUD uses it to choose
between a Level readout and a clock. `check_objective()` runs once per unpaused
frame and is the only place a run can end without topping out. It sets `over`
plus either `cleared` or `timed_out`, and `draw()` turns that into the panel
title (`CLEARED` / `TIME UP` / `GAME OVER`).

Time-ranked modes sort **ascending** — fastest first — via `entry_better()`.
`qualifies()` refuses an entry with no recorded time, so an abandoned Sprint can
never post an unbeatable short time. `run_game()` only stamps `elapsed_ms` when
`cleared` is set, which is the other half of that guard.

### Screen state machine

`main()` does essentially nothing: it initialises ncurses, loads scores, then
loops on a `Screen` value (`SCR_MENU`, `SCR_GAME`, `SCR_SCORES`, `SCR_QUIT`),
dispatching to `run_menu()`, `run_game()` or `run_scores()`. Each of those
returns the screen to go to next, so navigation is data, not call nesting.

`run_game()` owns one game: it plays the loop to completion, then offers the
initials prompt if the score qualifies, then hands off to `run_game_over()`.
Retry is just `run_game()` returning `SCR_GAME`, which re-enters it.

Every screen loop follows the same shape: check `screen_too_small()`, `erase()`,
draw, `refresh()`, then drain all pending keypresses with a non-blocking
`getch()` before `napms(16)`. Keep that pattern — it is what makes the ~60 fps
loop and independent gravity work.

### Rendering

- `SHAPE_SRC` holds only the **spawn orientation** of each tetromino. The other
  three rotations are generated at start-up in `init_shapes()`. Never hand-write
  rotation tables.
- The board stores `0` for empty and `piece + 1` for a settled cell, so the
  stored value *is* the ncurses colour-pair index. Intentional.
- `compute_layout()` runs every frame, so resizes are picked up for free.
- `draw_panel_box()` / `panel_center()` / `board_panel()` are the reusable
  panel primitives. `board_panel()` sizes itself to its longest line and is
  capped at the board width.
- **Never centre table rows independently.** The leaderboard uses one shared
  left edge (`TABLE_W`) via `put_str()`; centring each line on its own shears
  the columns apart, because rows differ in length. This bug has been fixed once
  already.
- `center_text()` clamps negative `x` to 0. That is deliberate — clipping beats
  a negative `mvaddstr` writing off-screen.

### High scores

Plain text at `$XDG_DATA_HOME/terminal-tetris/scores`, falling back to
`~/.local/share/terminal-tetris/scores`. Directory is created `0700`; failures
to create or write are swallowed on purpose, because losing a score table must
never stop the game from being playable.

Line format, one entry per line, comments start with `#`:

```
<mode-id> <initials> <score> <level> <lines> <YYYY-MM-DD> [<elapsed_ms>]
```

The trailing time is **optional on purpose**: files written before timed modes
existed must keep loading, and a row without a time sorts last on a time-ranked
board. Parse it with a `>= 6` check on the `sscanf` return, not `== 7`, and
`memset` the entry first so the field is defined when the conversion is absent.

`insert_score()` maintains a sorted top-`MAX_SCORES`, so reading the file **in
any order** gives the same result. That is what makes a hand-edited file safe.

Parsing is defensive and must stay that way. It skips malformed rows, rows with
too few fields, rows for unknown mode ids, and anything starting with `#`.
`clean_initials()` forces names to three characters from `[A-Z0-9]` (everything
else becomes `-`), which is what stops a hand-edited file from injecting
terminal escape sequences into the UI. Do not relax this.

## Testing

Compiles clean with `-Wall -Wextra`. Please keep it that way:

```sh
gcc -Wall -Wextra tetris.c -o tetris -lncurses
```

`tests/run_tests.sh` builds the game, generates the variants described below,
and runs the three suites against it — 38 checks covering the four mode HUDs,
scoring, pause, size gating, score-file parsing, and both end conditions
end-to-end. Build artifacts, the venv and the score tables all go to
`$TETRIS_WORK` (default `/tmp/terminal-tetris-test`), so the runner never writes
into the repo. It finishes by asserting `tetris.c` is unchanged from HEAD and
that the constants the variants shorten still hold their shipped values.

The game is a full-screen TUI, so it cannot be run in a plain shell — it needs a
pty. The pattern that works:

- Allocate a pty (`pty.fork()` in Python), set the window size with
  `TIOCSWINSZ`, and drive it with real key sequences from `curses.tigetstr`
  (`kcub1`, `kcuf1`, `kcuu1`, `kcud1`, `kent`).
- Decode the output with `pyte` (installed into a **venv**, never system
  Python) to read back the screen.
- Answer `\x1b[6n` cursor-position queries, or ncurses blocks waiting for a
  reply.
- **Use a terminfo without `rep` (e.g. `TERM=linux` or `vt100`) when checking
  layout.** ncurses uses REP to compress runs of identical characters such as
  box-drawing borders, and pyte does not implement REP — so `TERM=xterm-256color`
  makes pyte render collapsed borders and misreport column positions. This
  produces convincing but entirely fake "bugs".
- Point `XDG_DATA_HOME` at a temp directory so tests never touch real scores.

Two traps worth knowing, both of which produce *convincing fake bugs*:

- **Teardown hangs on the initials prompt.** If a run ends with a qualifying
  score, the game sits waiting for initials. A bare `q` just types a letter into
  it, so the child never exits and an unbounded `waitpid` blocks forever. Send
  `Esc` first to dismiss the prompt, then reap with `WNOHANG` in a bounded loop,
  with `SIGKILL` as the backstop.
- **Reading the active piece has to scan vertically.** The piece spawns at box
  `x = 3`, but gravity can tick between a lock and your read, moving it to
  `y = 1` before you look — so matching only at `y = 0` fails intermittently and
  then keeps failing for the whole fall. Scan `y` offsets 0..8 for the
  rotation-0 pattern. The vertical position is irrelevant anyway: the landing
  row is the same wherever the piece currently sits, so all you need is its
  identity.

Exercising the end conditions needs a player, not just keypresses. A small
greedy placement bot is enough: keep your own board model, read only the piece
identity off the screen, and simulate each rotation/column to score placements
by lines cleared minus bumpiness, holes and max height. One of those cleared
Sprint's full 40 lines, which is what actually proved the goal path end to end.

For an end condition too slow to reach honestly — Ultra's 120-second clock,
which a bot that tops out first never sees — build a variant **in `/tmp`** with
the constant shortened (`sed` the `time_limit_sec` field of that mode's row) and
drive that instead. Same code path, different constant. Afterwards confirm the
shipped source still holds the real value; never test by editing the repo file.

Check by hand after touching rules or screens:

- Rotating flush against each of the four walls (wall kicks).
- Clearing a single line, and a tetris at once.
- Each mode's HUD: Level for Marathon and Expert, a counting-**up** clock plus
  `N/40` for Sprint, a counting-**down** clock for Ultra.
- Sprint ending at exactly 40 lines: `CLEARED` panel, a time written to the
  score file, and a TIME-ranked board with the fastest first.
- Stacking out: the initials prompt appears only if the score qualifies, `Esc`
  skips without saving, and `Enter` persists it.
- The score surviving a full restart — relaunch and check the leaderboard
  reads from disk, not just from memory.
- A deliberately corrupted score file (junk rows, unknown mode, over-long
  initials, raw escape bytes) loading without crashing.

## Git

Default branch is `main`. Do not commit the `tetris` binary — it is in
`.gitignore` and always will be. The score file lives outside the repo, so it is
never a commit risk.
