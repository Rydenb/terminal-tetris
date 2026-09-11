"""End-to-end: Dig out the garbage, reach CLEARED, record a time, persist it.

Runs against a variant with a single garbage row. Rather than keep a board
model, each attempt reads the ghost piece: the ghost is drawn where a hard drop
would land, so when it covers the bottom row's gap, dropping digs the row out.
Moves and rotations are free until the drop, so every rotation and column is
probed. An O can never plug a one-cell gap, so an attempt that finds no fit is
abandoned and retried.
"""
import os
import shutil
import sys

from harness import Harness

WORK = os.environ.get("TETRIS_WORK", "/tmp/terminal-tetris-test")
BIN = os.path.join(WORK, "tetris-dig-short")
DATA = os.path.join(WORK, "data-dig")
WIDTH = 10
fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("  " + detail if detail else ""))
    if not ok:
        fails.append(name)


def find(rows, needle, start=0):
    for i in range(start, len(rows)):
        if needle in rows[i]:
            return i
    return -1


def panel(rows, label):
    i = find(rows, label)
    if i < 0 or i + 1 >= len(rows):
        return None
    row = rows[i + 1]
    return row.rsplit("x", 1)[-1].strip() if "x" in row else row.strip()


def bottom_row(rows):
    """The board's bottom row, as 2-char cells."""
    board = [r for r in rows if r.lstrip().startswith("x")]
    if not board:
        return []
    r = board[-1]
    fx = r.index("x")
    return [r[fx + 1 + 2 * c:fx + 3 + 2 * c] for c in range(WIDTH)]


def open_dig(h):
    h.pump(1.3)
    for _ in range(4):                  # Marathon -> Sprint -> Ultra -> Expert -> Dig
        h.send("right", 0.3)


def attempt(initials, first):
    """One Dig run. Returns (outcome, rows) with outcome 'cleared' | 'nofit'."""
    h = Harness(BIN, data_home=DATA)
    open_dig(h)
    if first:
        rows = h.text()
        check("menu offers Dig after Expert", find(rows, "<  Dig  >") >= 0)
        check("menu shows the Dig blurb", find(rows, "garbage") >= 0)
    h.send("enter", 1.2)

    if first:
        rows = h.text()
        start = bottom_row(rows)
        check("variant starts with one garbage row",
              start.count("##") == WIDTH - 1 and start.count(". ") == 1,
              repr("".join(start)))
        check("HUD shows Garbage 1", panel(rows, "Garbage") == "1",
              "got %r" % panel(rows, "Garbage"))

    fit = False
    for rot in range(4):
        if rot:
            h.send("up", 0.08)
        for _ in range(WIDTH // 2):
            h.send("left", 0.04)
        for col in range(WIDTH):
            if col:
                h.send("right", 0.08)
            else:
                h.pump(0.08)
            if ". " not in bottom_row(h.text()):
                fit = True
                break
        if fit:
            break

    if not fit:
        h.close()
        return "nofit", None

    h.send(" ", 0.8)
    outcome = "cleared" if find(h.text(), "NEW HIGH SCORE") >= 0 else "unknown"
    if outcome == "cleared":
        for ch in initials:
            h.send(ch.encode(), 0.2)
        h.send("enter", 0.8)
    rows = h.text()
    h.send("q", 1.0)
    h.close()
    return outcome, rows


shutil.rmtree(DATA, ignore_errors=True)
os.makedirs(DATA, exist_ok=True)

outcome, rows = "nofit", None
for n in range(8):
    outcome, rows = attempt("DIG", first=(n == 0))
    if outcome != "nofit":
        break

check("a Dig run digs out the garbage and is offered initials",
      outcome == "cleared", "outcome=%s" % outcome)
if rows:
    check("game-over panel reads CLEARED", find(rows, "CLEARED") >= 0)
    check("HUD shows Garbage 0", panel(rows, "Garbage") == "0",
          "got %r" % panel(rows, "Garbage"))
    print("  -- cleared run --")
    for r in rows:
        if r.strip():
            print("     " + r.rstrip())

# ---- did the time land on disk? --------------------------------------------
path = os.path.join(DATA, "terminal-tetris", "scores")
body = open(path).read() if os.path.exists(path) else ""
print("  -- score file --")
for line in body.splitlines():
    print("     " + line)
entries = [l.split() for l in body.splitlines() if l.strip() and not l.startswith("#")]
dig = [e for e in entries if e[0] == "dig"]
check("one dig entry was saved, as DIG", len(dig) == 1 and dig[0][1] == "DIG",
      str(dig))
check("the cleared run records a non-zero time",
      len(dig) == 1 and len(dig[0]) == 7 and int(dig[0][-1]) > 0, str(dig))

# ---- does it survive a restart, on a TIME-ranked board? --------------------
h = Harness(BIN, data_home=DATA)
open_dig(h)
h.send("down", 0.3)
h.send("enter", 1.2)
rows = h.text()
hdr = [r for r in rows if "NAME" in r]
check("Dig board is headed HIGH SCORES -- Dig", find(rows, "HIGH SCORES  --  Dig") >= 0)
check("Dig board column header reads TIME", any("TIME" in r for r in hdr), str(hdr))
check("score survived a restart (read from disk)", find(rows, "DIG") >= 0)
h.close()

print()
print("FAILURES: %d" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
