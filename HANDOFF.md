# HANDOFF — chlopkow.pl archive

## Current state

Published and verified on 2026-10-18: https://itstomekk.github.io/chlopkow-pl/
Public repo `itstomekk/chlopkow-pl`, GitHub Pages from `main/docs`. Initial release `988e31f`.
GitHub Pages reported built for the exact release commit. Nine live files matched the local
release after newline normalization. Live Firefox desktop/mobile, legend navigation and 60
guestbook entries passed with no page errors. Four focused unit tests pass, including the
nested-table truncation regression.

Knowledge integration is local in the game project: `wiedza/archiwum-chlopkow-pl.md`, linked
from `wiedza/fakty-o-chlopkowie.md`. It points to the reusable corpus and separates historical
source claims, folklore and game fiction. No game-runtime changes, game commit or game deploy.

- 175 article records: 41 recovered full-view HTML pages and 134 listing intros. Some full-view
  pages were image-only, so the surviving page is not proof the original images were recovered.
- 60 recovered guestbook entries, 22 variants of the historical "Czy wiesz" module (not 22 independently verified facts).
- 219 gallery records across six categories; ZERO recovered image files. Gallery pages retain
  the captions and explain this loss. Do not describe the caption count as downloaded photos.
- Original crawl: 4,625 attempted URL/date keys, 928 successful page responses, 317 distinct HTML
  bodies, 3,059 404 responses, 638 transient failures. The queue is empty. No original process
  is still writing this archive.
- A separate recovery pass added 16 successful full-view captures for article IDs. Do not launch
  duplicate crawlers or overwrite the original manifest.

## Source and rebuild

Original private archive (outside git):
`C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie/references/chlopkow-pl-archiwum/`

Merged original + recovery snapshot:
`C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie/references/chlopkow-pl-archiwum/recovery-20261018/`

Use the merged snapshot, not the original manifest, to preserve the recovered full articles:

`python build.py --archive C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie/references/chlopkow-pl-archiwum/recovery-20261018`

Validation: `python -m unittest test_privacy -v` and `python validate.py`.
The latter checks every HTML page for internal links, contact candidates and active archived content,
and runs a Firefox desktop/mobile navigation test with external network requests blocked.
All 186 HTML pages passed the static checks. Browser navigation, history text, gallery warnings,
60 guestbook entries and mobile width passed. Screenshots are private scratch artifacts.

## Constraints

Tomek authorized publishing material from his old public site including people and guestbook,
with emails and phone numbers removed. GG numbers are also stripped. No private game reference
photos are included. No contact/submission forms, trackers or old active scripts are restored.
Original text can contain obsolete or erroneous claims; archive preservation is not fact verification.

One interactive archive session owns `build.py`, `safe_html.py`, `docs/` and `data/`. No cron writer.
Do not reconfigure models or restart Hermes. Game-runtime deployment is not authorized here.
