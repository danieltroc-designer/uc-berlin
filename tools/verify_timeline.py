"""Assert a slide's score is fully retired when the deck moves on.

Every card schedules its choreography on the timeline that enter() owns, so
leaving a slide should stop all of it: no cue still firing on a hidden slide,
no animations piling up across a loop. This is the check that the single
kill() actually covers both.

The Berlin loop has one scored card, the pipeline: its highlight is twelve
timed class changes per pass. If leaving the card did not retire them, the
highlight would keep walking a row nobody can see and be somewhere arbitrary
on the next visit.

    python tools/verify_timeline.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "uploadcare-simple.html"
PROFILE = ROOT / "tools" / "_profile" / "tl"
CHROME = (pathlib.Path.home()
          / ".cache/ms-playwright-stable/chromium-1223/chrome-mac-arm64"
          / "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")

HOLD = "playing=false; clearTimeout(timer); clearInterval(tickTimer);"
LIT = """[...document.querySelectorAll('.slide')[0].querySelectorAll('.bp-card')]
    .map((c,i)=>c.classList.contains('lit')?i:-1).filter(i=>i>=0)"""

fails = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}{'  ' + str(detail) if detail else ''}")
    if not ok:
        fails.append(label)


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE),
        executable_path=str(CHROME) if CHROME.exists() else None,
        headless=True, viewport={"width": 1920, "height": 1080},
        reduced_motion="no-preference", args=["--no-sandbox", "--disable-gpu"],
    )
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(DIST.as_uri())
    pg.wait_for_timeout(1200)
    pg.evaluate(HOLD)
    n = pg.evaluate("deck.slides.length")

    print("leaving the pipeline card stops its highlight")
    pg.evaluate("enter(0);" + HOLD)
    pg.wait_for_timeout(2100)                     # middle of the first step's slot
    check("highlight had started", pg.evaluate(LIT) == [0], pg.evaluate(LIT))
    pg.evaluate("enter(1);" + HOLD)
    pg.wait_for_timeout(4200)                     # two more steps would have fired
    check("no cue fires on the hidden card", pg.evaluate(LIT) == [0], pg.evaluate(LIT))

    print("inactive cards retire their motion")
    inactive = pg.evaluate("""[...document.querySelectorAll('.slide:not(.active)')]
        .reduce((n,s)=>n+s.getAnimations({subtree:true})
          .filter(a=>a.playState==='running').length,0)""")
    check("no animation keeps running on inactive cards", inactive == 0, f"{inactive} running")

    print("animations do not accumulate across a full loop")
    pg.evaluate("enter(0);" + HOLD)
    pg.wait_for_timeout(1000)
    base = pg.evaluate("document.getAnimations().length")
    for _ in range(3):                             # three passes over the deck
        for i in range(n):
            pg.evaluate(f"enter({i});" + HOLD)
            pg.wait_for_timeout(120)
    pg.evaluate("enter(0);" + HOLD)
    pg.wait_for_timeout(1000)
    end = pg.evaluate("document.getAnimations().length")
    check("running animation count stable", end <= base * 2 + 8, f"{base} -> {end}")

    print("re-entering the pipeline card replays it from the top")
    check("re-entry cleared the old highlight", pg.evaluate(LIT) == [], pg.evaluate(LIT))
    pg.wait_for_timeout(1100)
    check("and lights Upload again", pg.evaluate(LIT) == [0], pg.evaluate(LIT))

    check("no page errors", not errors, "; ".join(errors[:3]))
    ctx.close()

print("\nFAILED: " + ", ".join(fails) if fails else "\nall timeline checks passed")
sys.exit(1 if fails else 0)
