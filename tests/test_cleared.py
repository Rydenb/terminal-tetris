"""End-to-end: Sprint CLEARED, a recorded time, fastest-first ranking.

A topped-out Sprint legitimately shows NO initials prompt (elapsed_ms is only
stamped when the run is cleared, and qualifies() refuses a time-ranked entry
with no time), so a run that tops out is retried rather than asserted on.
"""
import os
import shutil
import sys

from harness import Harness

WORK = os.environ.get("TETRIS_WORK", "/tmp/terminal-tetris-test")
BIN = os.path.join(WORK, "tetris-narrow")
DATA = os.path.join(WORK, "data-narrow")
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


def attempt(initials, delay):
    """One Sprint run. Returns (outcome, panel_rows) where outcome is
    'cleared' | 'topout' | 'unknown'."""
    h = Harness(BIN, data_home=DATA)
    h.pump(1.3)
    h.send("right", 0.4)                # Marathon -> Sprint
    h.send("enter", 1.4)
    if delay:
        h.pump(delay)
    outcome = "unknown"
    for n in range(30):
        for _ in range(n % 4):          # sweep the four orientations
            h.send("up", 0.08)
        h.send(" ", 0.22)
        rows = h.text()
        if find(rows, "NEW HIGH SCORE") >= 0 or find(rows, "CLEARED") >= 0:
            outcome = "cleared"
            break
        if find(rows, "GAME OVER") >= 0:
            outcome = "topout"
            break
    if outcome == "cleared":
        # CLEARED and the initials prompt are two separate screens:
        # run_initials_entry() draws its own only once qualifies() says yes.
        # Sampling the screen once here races that redraw, and a missed prompt
        # means no initials, so no insert_score() and no save_scores() -- which
        # does not look like a timing problem at all by the time it surfaces,
        # as "two sprint entries were saved  got 1". Wait for the prompt.
        for _ in range(20):
            if find(h.text(), "NEW HIGH SCORE") >= 0:
                for ch in initials:
                    h.send(ch.encode(), 0.2)
                h.send("enter", 0.8)
                break
            h.pump(0.1)
    rows = h.text()
    h.send("q", 1.0)
    h.close()
    return outcome, rows


def cleared_run(initials, delay, tries=6):
    for _ in range(tries):
        outcome, rows = attempt(initials, delay)
        if outcome == "cleared":
            return rows
    return None


shutil.rmtree(DATA, ignore_errors=True)
os.makedirs(DATA, exist_ok=True)

rows1 = cleared_run("FST", 0)
check("a Sprint run reaches CLEARED", rows1 is not None)
if rows1:
    check("game-over panel reads CLEARED", find(rows1, "CLEARED") >= 0)
    print("  -- cleared run panel --")
    for r in rows1[8:14]:
        if r.strip():
            print("     " + r.strip())

rows2 = cleared_run("SLO", 1.6)
check("a second (slower) run reaches CLEARED", rows2 is not None)

path = os.path.join(DATA, "terminal-tetris", "scores")
body = open(path).read() if os.path.exists(path) else ""
print("  -- score file --")
for line in body.splitlines():
    print("     " + line)

rows = [l.split() for l in body.splitlines() if l.strip() and not l.startswith("#")]
sprint = [r for r in rows if r[0] == "sprint"]
check("two sprint entries were saved", len(sprint) == 2, "got %d" % len(sprint))
check("cleared runs record a non-zero time",
      bool(sprint) and all(int(r[-1]) > 0 for r in sprint),
      str([r[-1] for r in sprint]))
check("the faster run holds the smaller time",
      len(sprint) == 2 and int(sprint[0][-1]) < int(sprint[1][-1]),
      str([(r[1], r[-1]) for r in sprint]))

# ---- board order and column header -----------------------------------------
h = Harness(BIN, data_home=DATA)
h.pump(1.3)
h.send("right", 0.4)
h.send("down", 0.4)
h.send("enter", 1.3)
rows = h.text()
hdr = [r for r in rows if "NAME" in r]
check("Sprint board column header reads TIME", any("TIME" in r for r in hdr),
      str(hdr))
check("Sprint board header has no SCORE column", not any("SCORE" in r for r in hdr),
      str(hdr))
print("  -- whole Sprint scores screen --")
for r in rows:
    if r.strip():
        print("     " + r.strip())
order = "".join("F" if "FST" in r else "S" if "SLO" in r else ""
                for r in rows if "FST" in r or "SLO" in r)

# The board ranks by time, so whichever run holds the smaller time has to be
# listed first -- and that is not always FST. cleared_run() retries a run that
# topped out, and elapsed_ms is only stamped on the attempt that actually
# cleared, so the delay=0 run can end up the slower of the two. Asserting "FS"
# then contradicts a board that is sorting correctly. Read the expectation off
# the recorded times instead of assuming the delay decided the race.
by_time = sorted(sprint, key=lambda r: int(r[-1]))
expected = "".join("F" if r[1] == "FST" else "S" for r in by_time)
check("fastest run listed first", order == expected,
      "order=%r expected=%r" % (order, expected))
h.close()

print()
print("FAILURES: %d" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
