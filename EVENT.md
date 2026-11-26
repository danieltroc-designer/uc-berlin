# Berlin — event notes

Working source of truth for this booth cut. Do not invent event facts.

## Confirmed

- Working name: **Berlin**. The event's official name is not recorded here.
- This folder is an isolated clone of the Ecommerce Expo booth deck
  (`../ecommerce-expo` @ `3df8c5a`). It has no remote.
- The loop follows the "TV loop" storyboard (a Claude artifact, supplied as a
  screenshot on 26 Nov 2026): **43 seconds, 4 cards, 50" landscape**.
  1. **Pipeline** (24s: 12s, twice per loop). "Your entire file pipeline. /
     One integration." Six steps, each with a proof line, and a yellow
     highlight that steps along the row:
     - Upload — Any source, files up to 5 TB
     - Scan — Malware checked on arrival
     - Store — Ours or your own
     - Transform — Resize, crop, convert, optimize
     - Secure — Signed URLs, access logs
     - Deliver — Global CDN, 99.9% SLA
  2. **Logo wall** (5s). "Already running in production at" L'Oréal,
     SoundCloud, Zapier, Aryeo, Prezly, Sequoia.
  3. **Ownership** (6s). "Don't let file handling become your job."
  4. **Identity + raffle** (8s). Uploadcare lockup, "File infrastructure for
     the enterprise.", "Since 2011 · Stand [no]"; on the right half "Enter the
     raffle", "Win [prize]. Drawn [day] at [time].", a QR and "Scan to enter".
- Decisions made on the build, 26 Nov 2026:
  - **The raffle QR is the same code the previous decks used**:
    `assets/qr/booth-qr.png`, which decodes to `https://l.ead.me/bgyXox`.
    Both closing cards draw it.
  - **The logo wall has no boxes**; it follows the previous decks' wall
    (centred title, free-standing marks).
  - **The closing card is undecided between two versions**, both in the loop
    for comparison: B, the previous decks' globe outro with Berlin's copy, and
    A, the storyboard's split identity/raffle layout. The loop is 51s while
    both are in and 43s once one is removed.
- The storyboard's reasoning, kept because it decides the order: the stand's
  banner states the problem and claims it, the screen proves it and hands it
  back to the person in the room. The pipeline holds 24 of 43 seconds so a
  glance almost always lands on the message. The ownership card is the only
  one that speaks to the visitor directly and sits after the proof so it reads
  as a conclusion. The raffle also lives on an A5 card on the table, which
  does the close-range work.

## Open / TBD

From the storyboard's own "still open" list:

- Prize, draw day and time, stand number. On screen these are still the
  storyboard's bracketed placeholders.
- Sequoia reads as the VC: disambiguate, or swap for Zola. There is no Zola
  mark in `assets/logos/` yet.
- Screen orientation, portrait or landscape. The deck is built landscape.

Not answered by the storyboard:

- Which closing card stays, A or B.
- Whether `https://l.ead.me/bgyXox` already lands on the Berlin raffle page.
  The code is the previous event's by decision; where the short link points is
  set on the link service, not here, and has not been checked for Berlin.
- Event dates and venue.
- Whether the proof lines need sign-off as claims: "files up to 5 TB",
  "99.9% SLA", "Since 2011". They were read off a small screenshot; check them
  against the full-size storyboard.
- The storyboard's full-size `pipeline-card.png`, which this project has not
  seen. Card 1 and its six icons were built from the thumbnail.

## Assets still needed

- Zola logo as SVG, if it replaces Sequoia
- The pipeline card's real icon set, if design has one

## Inherited from Ecommerce Expo

The seven Ecommerce Expo cards are no longer in the loop. Their card types,
assets and notes remain in the project for reuse: the Zephyr quote, the
catalog-admin demo, the six-logo Expo wall, the LEGO giveaway line. None of it
is a Berlin fact. See `../ecommerce-expo/EVENT.md` for that event's record.
