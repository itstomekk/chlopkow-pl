# chlopkow-pl archive ownership

Canonical project: `C:/Users/Lenovo/Hermes/projects/websites/chlopkow-pl`.
Read PLAN.md, HANDOFF.md and README.md before changing the build.

| Path | Writer | Rule |
|---|---|---|
| `build.py`, `safe_html.py`, `docs/`, `data/` | one interactive archive session | No cron or parallel builders. Preserve raw archive separately; validate before publication. |

The old public site's content and guestbook are authorized for publication, except email,
phone and GG numbers. Do not import private game photos. `references/` and raw captures stay
outside this repo. Do not run the crawler if its previous process is still active.

Publishing this archive does not authorize deploying or committing unrelated game changes.
