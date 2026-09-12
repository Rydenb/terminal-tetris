"""End-to-end: Ultra times out, offers initials, saves, and persists."""
import os
import shutil
import sys

from harness import Harness

WORK = os.environ.get("TETRIS_WORK", "/tmp/tetrisplus-test")
BIN = os.path.join(WORK, "tetris-ultra-short")
DATA = os.path.join(WORK, "data-ultra")
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


shutil.rmtree(DATA, ignore_errors=True)
os.makedirs(DATA, exist_ok=True)

h = Harness(BIN, data_home=DATA)
h.pump(1.3)
h.send("right", 0.4)
h.send("right", 0.4)
h.send("enter", 1.4)

# Score something so the run qualifies, then let the 3s clock expire.
for _ in range(3):
    h.send(" ", 0.35)
score = panel(h.text(), "Score")
check("scored before the clock expired", score is not None and int(score) > 0, "score=%s" % score)

h.pump(4.5)
rows = h.text()
# The prompt draws on top of the panel the moment the run ends, so TIME UP is
# only observable once the run is dismissed -- assert it on the game-over
# screen below, and assert the prompt is what appeared first.
check("initials prompt is offered", find(rows, "NEW HIGH SCORE") >= 0)
h.dump("AFTER TIMEOUT")

# Type initials and save.
h.send(b"a", 0.25)
h.send(b"b", 0.25)
h.send(b"c", 0.25)
h.send("enter", 0.8)
rows = h.text()
check("timed-out run shows the TIME UP panel", find(rows, "TIME UP") >= 0)
check("game-over panel offers retry/menu/quit",
      find(rows, "retry") >= 0 and find(rows, "menu") >= 0)
print("  -- game-over screen --")
for r in rows:
    if r.strip():
        print("     " + r.strip())

h.send("q", 1.0)
h.close()

# ---- did it land on disk? ---------------------------------------------------
path = os.path.join(DATA, "tetrisplus", "scores")
check("score file was created", os.path.exists(path))
body = open(path).read() if os.path.exists(path) else ""
print("  -- score file --")
for line in body.splitlines():
    print("     " + line)
check("file has a comment header", body.lstrip().startswith("#"))
check("entry is for the ultra mode", "ultra" in body)
check("initials were uppercased to ABC", " ABC " in body or body.split()[-6:-1].count("ABC") > 0,
      "looking for ABC")
check("timed-out run records no time (trailing 0)",
      any(l.split()[0] == "ultra" and l.split()[-1] == "0" for l in body.splitlines() if l.strip() and not l.startswith("#")))

# ---- does it survive a restart? --------------------------------------------
h = Harness(BIN, data_home=DATA)
h.pump(1.3)
h.send("right", 0.4)
h.send("right", 0.4)
h.send("down", 0.4)
h.send("enter", 1.3)
rows = h.text()
check("score survived a restart (read from disk)", find(rows, "ABC") >= 0)
check("no 'No scores yet' banner", find(rows, "No scores yet") == -1)
print("  -- leaderboard after restart --")
for r in rows[4:12]:
    if r.strip():
        print("     " + r.strip())
h.close()

print()
print("FAILURES: %d" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
