"""Assert the Berlin loop against its storyboard: order, timing and geometry.

The four Berlin cards were laid out from a screenshot, not a Figma frame, so
there are no frame numbers to compare with. What is checked instead is what
would actually break at a stand:

  * the loop is in the storyboard's order and 43s long (+8s if a second
    closer is ever put back in to be compared)
  * nothing overflows its box, and nothing leaves the 1920x1080 stage
  * the pipeline's highlight frame sits exactly on one step at a time, in
    order, twice, is gone between passes, and replays on a second visit
  * the logo wall is six free-standing marks on their slots, with no cells
  * the closer's geometry is the previous decks' outro to the pixel, it draws
    the QR, and its raffle copy is the confirmed wording
  * every card is fully built under reduced motion, with nothing lit
  * the layout is unchanged when the stage is scaled down to a laptop

    python tools/check_berlin.py            # asserts; writes tools/_shots/berlin-*.png
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "uploadcare-simple.html"
OUT = ROOT / "tools" / "_shots"
PROFILE = ROOT / "tools" / "_profile" / "berlin"
CHROME = (pathlib.Path.home()
          / ".cache/ms-playwright-stable/chromium-1223/chrome-mac-arm64"
          / "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")

CORE = ["berlinPipeline", "berlinLogos", "berlinOwnership"]
CLOSERS = {"berlinOutro", "berlinIdentity"}
STEPS = ["Upload", "Scan", "Store", "Transform", "Secure", "Deliver"]
RAFFLE = ("Enter the raffle. Win a Lego Polaroid OneStep camera. "
          "Drawn at the stand on Tuesday, 3:15 PM.")
WALL = [(510, 455), (960, 455), (1410, 455), (510, 620), (960, 620), (1410, 620)]
HOLD = "playing=false; clearTimeout(timer); clearInterval(tickTimer);"

fails = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}{'  ' + str(detail) if detail else ''}")
    if not ok:
        fails.append(label)


# Layout boxes in stage pixels, from offsets rather than rects, so the numbers
# are the same whatever the viewport scales the stage to.
BOX = """(sel)=>[...document.querySelectorAll('.slide.active '+sel)].map(el=>{
  let x=0,y=0,n=el; const stage=document.getElementById('stage');
  while(n && n!==stage){ x+=n.offsetLeft; y+=n.offsetTop; n=n.offsetParent; }
  return {x,y,w:el.offsetWidth,h:el.offsetHeight,sw:el.scrollWidth,sh:el.scrollHeight};
})"""

LIT = "[...document.querySelectorAll('.slide.active .bp-card')].map((c,i)=>c.classList.contains('lit')?i:-1).filter(i=>i>=0)"

# The highlight frame: its opacity, and which panel it is standing on. The x
# comes out of the computed transform, which is in layout pixels however the
# stage is scaled; -1 means it is between panels.
FRAME = """(()=>{const hl=document.querySelector('.slide.active .bp-hl');
  const cs=getComputedStyle(hl), x=new DOMMatrix(cs.transform).m41;
  const on=[...document.querySelectorAll('.slide.active .bp-card')]
    .findIndex(c=>Math.abs(c.offsetLeft-x)<=.5);
  return {op:+cs.opacity, on, x:Math.round(x*10)/10,
          w:hl.offsetWidth, h:hl.offsetHeight};})()"""

# the drawn QR as a string of module rectangles, to compare two cards' codes
QR_SIG = """(sel)=>{const s=document.querySelector('.slide.active '+sel+' svg');
  return s ? [...s.querySelectorAll('path,rect')].map(n=>n.getAttribute('d')
    ||[n.getAttribute('x'),n.getAttribute('y'),n.getAttribute('width')].join(',')).join('|') : ''}"""


def launch(p, tag, size, reduced=False):
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE / tag),
        executable_path=str(CHROME) if CHROME.exists() else None,
        headless=True, viewport={"width": size[0], "height": size[1]},
        reduced_motion="reduce" if reduced else "no-preference",
        args=["--no-sandbox", "--disable-gpu"],
    )
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(DIST.as_uri())
    pg.wait_for_timeout(1000)
    pg.evaluate(HOLD)
    return ctx, pg, errors


def geometry(pg, tag, types):
    """Every card's boxes. Returned so two viewports can be compared."""
    seen = {}
    at = {t: i for i, t in enumerate(types)}

    def boxes(sel):
        got = pg.evaluate(BOX, sel)
        seen[sel] = got
        return got

    def inside(b, pad=0):
        return b["x"] >= pad and b["y"] >= pad and b["x"] + b["w"] <= 1920 - pad \
            and b["y"] + b["h"] <= 1080 - pad

    print(f"[{tag}] card 1 — pipeline")
    pg.evaluate("enter(0);" + HOLD)
    pg.wait_for_timeout(1100)
    cards = boxes(".bp-card")
    check("six steps", len(cards) == 6, len(cards))
    check("steps are 280x340", all(c["w"] == 280 and c["h"] == 340 for c in cards),
          [(c["w"], c["h"]) for c in cards][:2])
    check("row spans the 80px margins", cards[0]["x"] == 80 and cards[-1]["x"] + cards[-1]["w"] == 1840,
          (cards[0]["x"], cards[-1]["x"] + cards[-1]["w"]))
    check("16px gutters", all(cards[i + 1]["x"] - cards[i]["x"] - cards[i]["w"] == 16 for i in range(5)))
    names = pg.evaluate("[...document.querySelectorAll('.slide.active .bp-step')].map(e=>e.textContent)")
    check("steps in pipeline order", names == STEPS, names)
    sla = pg.evaluate("[...document.querySelectorAll('.slide.active .bp-proof')].pop().textContent")
    check("Deliver claims the 99.99% SLA", " ".join(sla.split()) == "Global CDN, 99.99% SLA", sla)
    # the copy column is 216px; a proof line wider than that would be clipped
    # by nothing and simply run over the panel's padding
    proofs = boxes(".bp-proof")
    check("proof lines fit their column", all(b["sw"] <= 216 for b in proofs),
          [b["sw"] for b in proofs])
    lines = pg.evaluate("""[...document.querySelectorAll('.slide.active .bp-proof')].map(e=>
        Math.round(e.offsetHeight/parseFloat(getComputedStyle(e).lineHeight)))""")
    check("proof lines are at most two lines", max(lines) <= 2, lines)
    head, logo = boxes(".bp-head")[0], boxes(".bp-logo")[0]
    check("headline clears the lockup", head["x"] + head["w"] + 80 <= logo["x"],
          (head["x"] + head["w"], logo["x"]))
    check("lockup ends on the right margin", abs(logo["x"] + logo["w"] - 1840) <= 1, logo)
    check("headline clears the row", head["y"] + head["h"] + 120 <= cards[0]["y"],
          (head["y"] + head["h"], cards[0]["y"]))
    # the masked lines: 30px between the first line's baseline and the second
    # line's cap tops, which the mask's padding must not have disturbed
    caps = boxes(".bp-line > span")
    check("30px between the headline's two lines",
          len(caps) == 2 and abs(caps[1]["y"] - caps[0]["y"] - caps[0]["h"] - 30) <= 1,
          [(c["y"], c["h"]) for c in caps])
    frame = pg.evaluate(FRAME)
    check("highlight frame is a panel's size", frame["w"] == 280 and frame["h"] == 340, frame)

    print(f"[{tag}] card 2 — logo wall")
    pg.evaluate("enter(1);" + HOLD)
    pg.wait_for_timeout(1100)
    marks = boxes(".bl-logo")
    check("six marks", len(marks) == 6, len(marks))
    check("no cells around them", pg.evaluate(
        """[...document.querySelectorAll('.slide.active .bl-logo')].every(e=>{
            const c=getComputedStyle(e);
            return c.borderTopWidth==='0px' && c.backgroundColor==='rgba(0, 0, 0, 0)'})"""))
    check("every customer is a real vector", pg.evaluate(
        "document.querySelectorAll('.slide.active .bl-logo svg').length") == 6)
    off = [(round(m["x"] + m["w"] / 2 - cx, 1), round(m["y"] + m["h"] / 2 - cy, 1))
           for m, (cx, cy) in zip(marks, WALL)]
    check("each mark is centred on its slot", all(abs(dx) <= 1 and abs(dy) <= 1 for dx, dy in off), off)
    title = boxes(".bl-title")[0]
    check("title is centred on the stage", abs(title["x"] + title["w"] / 2 - 960) <= 1, title)
    check("title clears the marks", title["y"] + title["h"] + 120 <= min(m["y"] for m in marks),
          (title["y"] + title["h"], min(m["y"] for m in marks)))
    check("marks stay inside the stage", all(inside(m, 80) for m in marks))

    print(f"[{tag}] card 3 — ownership")
    pg.evaluate("enter(2);" + HOLD)
    pg.wait_for_timeout(1300)
    lines3 = boxes(".bo-line")
    check("two hand-broken lines", len(lines3) == 2, len(lines3))
    check("line stays inside the stage", all(b["x"] + b["w"] <= 1920 - 136 for b in lines3),
          [b["x"] + b["w"] for b in lines3])
    mid = (lines3[0]["y"] + lines3[-1]["y"] + lines3[-1]["h"]) / 2
    check("line is centred on the stage's height", abs(mid - 540) <= 2, mid)
    acc = pg.evaluate("[...document.querySelectorAll('.slide.active .bo-w.acc')].map(e=>e.textContent).join(' ')")
    check("yellow phrase", acc == "your job.", acc)
    same = pg.evaluate("""(()=>{const a=[...document.querySelectorAll('.slide.active .bo-w.acc')];
        return new Set(a.map(e=>e.offsetTop)).size===1 && a.every(e=>e.parentNode===a[0].parentNode)})()""")
    check("yellow phrase is on one line", same)

    sigs = {}
    if "berlinOutro" in at:
        print(f"[{tag}] card 4 — the raffle outro")
        pg.evaluate(f"deck.slides[{at['berlinOutro']}].float=false;"
                    f"deck.slides[{at['berlinOutro']}].typing=false;renderDeck();"
                    f"enter({at['berlinOutro']});" + HOLD)
        pg.wait_for_timeout(1500)
        # the previous decks' frame, to the pixel: these are the numbers the
        # inherited outro was measured at before Berlin's copy went into it
        for sel, want in ((".hb-sign", (867, 186, 185, 33)), (".hb-mark", (916, 497, 86, 86)),
                          (".hb-outro-qr", (857, 711, 204, 204))):
            b = boxes(sel)[0]
            got = (b["x"], b["y"], b["w"], b["h"])
            check(f"{sel} is where the previous outro has it",
                  all(abs(g - w) <= 1 for g, w in zip(got, want)), got)
        line = boxes(".hb-outro-line")[0]
        check("headline is two lines", 120 < line["h"] < 170, line["h"])
        check("headline clears the glyph", line["y"] + line["h"] + 20 <= 497, line["y"] + line["h"])
        sub, qr = boxes(".hb-outro-sub")[0], boxes(".hb-outro-qr")[0]
        # 14px is the previous outro's own gap for a two-line sign-off; the
        # code's box is mostly quiet zone, so the ink is a further ~20px down
        check("sign-off is two lines and clears the code",
              sub["y"] + sub["h"] + 12 <= qr["y"], (sub["y"] + sub["h"], qr["y"]))
        check("nothing is set under the code", pg.evaluate(
            "!document.querySelector('.slide.active .hb-outro-meta')"))
        # the raffle copy, as confirmed in EVENT.md, with no placeholder left
        said = pg.evaluate("document.querySelector('.slide.active .hb-outro-sub').innerText")
        check("raffle copy is the confirmed wording", " ".join(said.split()) == RAFFLE, said)
        check("no bracketed placeholder is left on the card", "[" not in pg.evaluate(
            "document.querySelector('.slide.active').innerText"))
        # the second line is the wide one and runs across the globe: it has to
        # stay clear of the corner files' telemetry on both sides
        wide = pg.evaluate("""(()=>{const el=document.querySelector('.slide.active .hb-outro-sub');
            const r=document.createRange(); r.selectNodeContents(el);
            const k=document.getElementById('stage').getBoundingClientRect().width/1920;
            const b=r.getBoundingClientRect(), s=document.getElementById('stage').getBoundingClientRect();
            return [(b.left-s.left)/k, (b.right-s.left)/k]})()""")
        check("sign-off stays inside the centre column", wide[0] >= 480 and wide[1] <= 1440,
              [round(w) for w in wide])
        # the prize is picked out in brand yellow — colour only, so the line
        # is exactly as wide as it was without it
        hl = pg.evaluate("""(()=>{const el=document.querySelector('.slide.active .hb-outro-sub .hb-hl');
            if(!el) return null; const cs=getComputedStyle(el);
            return {text:el.textContent, ink:cs.color, bg:cs.backgroundColor}})()""")
        check("the prize is picked out", bool(hl) and hl["text"] == "Lego Polaroid OneStep camera", hl and hl["text"])
        check("in brand yellow, with no plate behind it", bool(hl) and hl["ink"] == "rgb(255, 207, 62)"
              and hl["bg"] == "rgba(0, 0, 0, 0)", hl and (hl["ink"], hl["bg"]))
        check("globe and the four corner files are there", pg.evaluate(
            "!!document.querySelector('.slide.active .hb-globe svg') && "
            "document.querySelectorAll('.slide.active .hb-node').length") == 4)
        sigs["outro"] = pg.evaluate(QR_SIG, ".hb-outro-qr")
        check("the code is drawn", len(sigs["outro"]) > 200, len(sigs["outro"]))

    if "berlinIdentity" not in at:
        return seen, sigs
    print(f"[{tag}] split raffle (only if it is in the deck)")
    pg.evaluate(f"enter({at['berlinIdentity']});" + HOLD)
    pg.wait_for_timeout(1300)
    panel = boxes(".bi-raffle")[0]
    check("raffle takes the right half", panel["x"] == 950 and panel["x"] + panel["w"] == 1920, panel)
    for sel in (".bi-lockup", ".bi-tag", ".bi-meta"):
        b = boxes(sel)[0]
        check(f"{sel} stays left of the raffle panel", b["x"] >= 112 and b["x"] + b["w"] + 60 <= 950,
              (b["x"], b["x"] + b["w"]))
    for sel in (".bi-rt", ".bi-rs", ".bi-qr", ".bi-scan"):
        b = boxes(sel)[0]
        check(f"{sel} stays inside the stage", inside(b, 60), b)
    qr = boxes(".bi-qr")[0]
    check("QR plate is 280px square", qr["w"] == 280 and qr["h"] == 280, qr)
    tbc = pg.evaluate("!!document.querySelector('.slide.active .bi-qr-tbc')")
    check("the code is drawn, not the placeholder plate", not tbc)
    sigs["split"] = pg.evaluate(QR_SIG, ".bi-qr")
    if "outro" in sigs:
        check("both closers draw the same code", sigs["split"] == sigs["outro"] and sigs["split"] != "")
    return seen, sigs


with sync_playwright() as p:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- 1:1
    ctx, pg, errors = launch(p, "norm", (1920, 1080))
    print("loop")
    slides = pg.evaluate("deck.slides.map(s=>[s.type,s.duration])")
    types = [s[0] for s in slides]
    closers = types[len(CORE):]
    check("pipeline, logos, ownership, in storyboard order", types[:len(CORE)] == CORE, types)
    check("then the closer — one, or both while they are being compared",
          1 <= len(closers) <= 2 and set(closers) <= CLOSERS and len(set(closers)) == len(closers),
          closers)
    total, want = sum(s[1] for s in slides), 43 + 8 * (len(closers) - 1)
    check(f"loop is {want}s (43s per storyboard, +8s per extra closer)", total == want, total)
    check("pipeline holds 24 of them, in two passes",
          slides[0][1] == 24 and pg.evaluate("deck.slides[0].passes") == 2)
    check("Commit Mono loaded", pg.evaluate("document.fonts.check(\"18px 'Commit Mono'\")"))

    full, _ = geometry(pg, "1920x1080", types)

    print("pipeline highlight")
    pg.evaluate("enter(0);" + HOLD)
    t0 = 0
    # mid-slot of every step of both passes, plus the two unlit leads
    probes = [(600, [])] + [(1200 + i * 1800 + 900, [i]) for i in range(6)] \
        + [(12600, [])] + [(13200 + i * 1800 + 900, [i]) for i in range(6)]
    walked = framed = True
    for t, want in probes:
        pg.wait_for_timeout(t - t0)
        t0 = t
        got, fr = pg.evaluate(LIT), pg.evaluate(FRAME)
        if got != want:
            walked = False
            print(f"        at {t}ms lit={got} want={want}")
        # the frame is settled on the lit step, or invisible when none is
        good = (fr["op"] == 1 and fr["on"] == want[0]) if want else fr["op"] < .02
        if not good:
            framed = False
            print(f"        at {t}ms frame={fr} want on={want}")
        if t in (600, 5700, 12600, 23100):     # entrance, Store, the lead, Deliver
            pg.screenshot(path=str(OUT / f"berlin-0-{t}.png"))
    check("one step lit at a time, in order, twice, with an unlit lead", walked)
    check("the frame stands exactly on the lit step, and is gone between passes", framed)
    # ten hops in: each one cancels its predecessor, so one is alive, not ten
    hops = pg.evaluate("""document.querySelector('.slide.active .bp-hl').getAnimations()
        .filter(a=>'transform' in (a.effect.getKeyframes()[0]||{})).length""")
    check("finished hops are not left stacked on the frame", hops == 1, hops)

    # The Upload -> Scan hop, sampled every frame in the page: the frame has to
    # be seen *between* the panels (it travels, it does not cut), stay fully
    # visible while it does, carry a few pixels past its mark and come back.
    pg.evaluate("""enter(0); playing=false; clearTimeout(timer); clearInterval(tickTimer);
      window.__hop=[]; (()=>{const hl=document.querySelector('.slide.active .bp-hl');
        const t0=performance.now();
        (function f(){const cs=getComputedStyle(hl);
          __hop.push([performance.now()-t0, new DOMMatrix(cs.transform).m41, +cs.opacity]);
          if (performance.now()-t0 < 4300) requestAnimationFrame(f);})();})()""")
    pg.wait_for_timeout(3200)
    pg.screenshot(path=str(OUT / "berlin-0-hop.png"))
    pg.wait_for_timeout(1300)
    hop = [s for s in pg.evaluate("window.__hop") if 2900 <= s[0] <= 4200]
    between = [s for s in hop if 4 < s[1] < 292]
    peak = max(s[1] for s in hop)
    check("the frame travels between steps", len(between) >= 5, f"{len(between)} frames in flight")
    check("and stays fully visible while it does", all(s[2] == 1 for s in between))
    check("it carries past its mark and settles back", 297 < peak < 312 and abs(hop[-1][1] - 296) <= .5,
          f"peak {peak:.1f}px, rests at {hop[-1][1]:.1f}px")

    pg.evaluate("enter(1);" + HOLD)
    pg.wait_for_timeout(300)
    pg.evaluate("enter(0);" + HOLD)
    check("re-entry starts unlit", pg.evaluate(LIT) == [] and pg.evaluate(FRAME)["op"] < .02)
    pg.wait_for_timeout(2100)
    check("second visit replays from Upload",
          pg.evaluate(LIT) == [0] and pg.evaluate(FRAME)["on"] == 0, pg.evaluate(LIT))
    shots = [(1, 1500), (2, 400), (2, 1500)] + [(i, 3000) for i in range(len(CORE), len(types))]
    for i, t in shots:
        pg.evaluate(f"enter({i});" + HOLD)
        pg.wait_for_timeout(t)
        pg.screenshot(path=str(OUT / f"berlin-{i}-{t}.png"))
    check("no page errors", not errors, "; ".join(errors[:3]))
    ctx.close()

    # ------------------------------------------------------------ laptop
    ctx, pg, errors = launch(p, "small", (1280, 800))
    small, _ = geometry(pg, "1280x800", types)
    print("scaled stage")
    check("layout is identical when the stage is scaled", small == full)
    # the frame's travel is the thing that would be wrong by the scale factor
    pg.evaluate("enter(0);" + HOLD)
    pg.wait_for_timeout(1200 + 1800 * 2 + 900)
    fr = pg.evaluate(FRAME)
    check("the frame still lands on its step when the stage is scaled",
          fr["op"] == 1 and fr["on"] == 2, fr)
    check("no page errors", not errors, "; ".join(errors[:3]))
    ctx.close()

    # ---------------------------------------------------- reduced motion
    ctx, pg, errors = launch(p, "red", (1920, 1080), reduced=True)
    print("reduced motion")
    for i, sel in ((0, ".bp-card"), (1, ".bl-logo"), (2, ".bo-w")):
        pg.evaluate(f"enter({i});" + HOLD)
        pg.wait_for_timeout(120)
        op = pg.evaluate(f"""[...document.querySelectorAll('.slide.active {sel}')]
            .map(e=>+getComputedStyle(e).opacity)""")
        check(f"card {i + 1} opens built", bool(op) and min(op) == 1, min(op) if op else "none")
        if i == 0:
            head = pg.evaluate("""[...document.querySelectorAll('.slide.active .bp-line > span')]
                .map(e=>getComputedStyle(e).transform)""")
            check("headline is in place", all(h == "none" for h in head), head)
            pg.wait_for_timeout(2400)
            check("no step is lit, and no frame", pg.evaluate(LIT) == []
                  and pg.evaluate(FRAME)["op"] == 0, pg.evaluate(LIT))
        pg.screenshot(path=str(OUT / f"berlin-red-{i}.png"))
    for i in range(len(CORE), len(types)):
        pg.evaluate(f"enter({i});" + HOLD)
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / f"berlin-red-{i}.png"))
    check("no page errors", not errors, "; ".join(errors[:3]))
    ctx.close()

print("\nFAILED: " + ", ".join(fails) if fails else "\nall Berlin checks passed")
sys.exit(1 if fails else 0)
