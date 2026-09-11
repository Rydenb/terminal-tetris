"""Functional checks against the real binary, covering README/CLAUDE.md claims.

Note: the HUD panel shares screen rows with the board, so fields must be read
from the panel column (right of the board's last vertical border), not off the
whole row.
"""
import os
import shutil
import sys

from harness import Harness

WORK = os.environ.get("TETRIS_WORK", "/tmp/terminal-tetris-test")
BIN = os.path.join(WORK, "tetris")
DATA = os.path.join(WORK, "data")
fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("  " + detail if detail else ""))
    if not ok:
        fails.append(name)


def fresh():
    shutil.rmtree(DATA, ignore_errors=True)
    os.makedirs(DATA, exist_ok=True)


def find(rows, needle, start=0):
    for i in range(start, len(rows)):
        if needle in rows[i]:
            return i
    return -1


def panel(rows, label):
    """Value of a HUD field: the panel column of the row after its label."""
    i = find(rows, label)
    if i < 0 or i + 1 >= len(rows):
        return None
    row = rows[i + 1]
    return row.rsplit("x", 1)[-1].strip() if "x" in row else row.strip()


def board(rows):
    """Board contents only, so frame columns don't mask a change."""
    out = []
    for r in rows:
        if r.count("x") >= 2:
            out.append(r[r.index("x") + 1:r.rindex("x")])
    return out


def ms(clock):
    """Parse m:ss.t into milliseconds, or None."""
    try:
        m, rest = clock.split(":")
        s, tenth = rest.split(".")
        return int(m) * 60000 + int(s) * 1000 + int(tenth) * 100
    except Exception:
        return None


def start(mode_rights=0, settle=1.4):
    fresh()
    h = Harness(BIN, data_home=DATA)
    h.pump(1.3)
    for _ in range(mode_rights):
        h.send("right", 0.4)
    h.send("enter", settle)
    return h


# ---- Sprint: clock counts UP, lines show N/40 -------------------------------
h = start(mode_rights=1)
rows = h.text()
check("Sprint HUD shows a Time label", find(rows, "Time") > 0)
check("Sprint HUD shows 0/40", panel(rows, "Lines") == "0/40",
      "got %r" % panel(rows, "Lines"))
check("Sprint HUD has no Level readout", find(rows, "Level") == -1)
t1 = ms(panel(rows, "Time"))
h.pump(1.2)
t2 = ms(panel(h.text(), "Time"))
check("Sprint clock counts UP", t1 is not None and t2 is not None and t2 > t1,
      "%s -> %s" % (panel(rows, "Time"), panel(h.text(), "Time")))
check("Sprint control block intact (M menu, Q quit)",
      find(rows, "M") > 0 and find(rows, "quit") > 0)
h.close()

# ---- Ultra: clock counts DOWN from 2:00 ------------------------------------
h = start(mode_rights=2)
rows = h.text()
u1 = ms(panel(rows, "Time"))
check("Ultra clock is under two minutes and running", u1 is not None and 0 < u1 <= 120000,
      "clock=%s" % panel(rows, "Time"))
h.pump(1.2)
u2 = ms(panel(h.text(), "Time"))
check("Ultra clock counts DOWN", u1 is not None and u2 is not None and u2 < u1,
      "%s -> %s" % (panel(rows, "Time"), panel(h.text(), "Time")))
check("Ultra shows plain line count, not N/40", find(rows, "/40") == -1)
h.close()

# ---- Marathon: score 0, hard drop and soft drop score ----------------------
h = start()
rows = h.text()
check("Marathon starts at score 0", panel(rows, "Score") == "0",
      "got %r" % panel(rows, "Score"))
check("Marathon shows a Level readout", find(rows, "Level") > 0)
h.send(" ", 1.0)
s_hard = int(panel(h.text(), "Score"))
check("hard drop scores (+2/cell)", s_hard > 0 and s_hard % 2 == 0, "score=%d" % s_hard)
h.send("down", 0.5)
s_soft = int(panel(h.text(), "Score"))
check("soft drop scores (+1/cell)", s_soft > s_hard, "%d -> %d" % (s_hard, s_soft))

# ---- pause freezes the board ------------------------------------------------
h.send("p", 0.7)
frozen = board(h.text())
h.send("right", 0.6)
h.send(" ", 0.6)
check("paused: board frozen against move and hard drop", board(h.text()) == frozen)
h.send("p", 0.6)

# ---- M returns to the menu --------------------------------------------------
h.send("m", 1.2)
rows = h.text()
check("M returns to the menu", find(rows, "High Scores") > 0 and find(rows, "T E T R I S") > 0)
h.close()

# ---- terminal size gating ---------------------------------------------------
h = Harness(BIN, cols=40, rows=20, data_home=DATA)
h.pump(1.4)
check("40x20 shows 'Terminal too small'", find(h.text(), "Terminal too small") > 0)
h.close()
h = Harness(BIN, cols=50, rows=22, data_home=DATA)
h.pump(1.4)
check("exactly 50x22 is usable", find(h.text(), "Terminal too small") == -1)
h.close()

# ---- corrupted score file ---------------------------------------------------
fresh()
d = os.path.join(DATA, "terminal-tetris")
os.makedirs(d, exist_ok=True)
with open(os.path.join(d, "scores"), "w") as f:
    f.write("# junk below\n")
    f.write("not a score line at all\n")
    f.write("nosuchmode ZZZ 9999 1 1 2026-01-01\n")
    f.write("marathon THISTOOLONGNAME 500 2 20 2026-01-01\n")
    f.write("marathon \x1b[31mRED 700 3 30 2026-01-01\n")
    f.write("marathon\n")
    f.write("sprint BOT notanumber x y z\n\n")
h = Harness(BIN, data_home=DATA)
h.pump(1.3)
h.send("down", 0.5)
h.send("enter", 1.3)
rows = h.text()
check("corrupted score file does not crash", any(r.strip() for r in rows))
check("no raw escape bytes reach the screen", not any("\x1b" in r for r in rows))
check("long initials are clamped to 3 chars", "THISTOOLONGNAME" not in "".join(rows))
print("  -- leaderboard as rendered --")
for r in h.text()[3:12]:
    if r.strip():
        print("     " + r.strip())
h.close()

print()
print("FAILURES: %d" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
