# Development

Technical notes for the chlopkow.pl archive. The welcoming overview is in [README.md](README.md).

Static rebuild of **Chłopków.pl**, the village website for Chłopków (gmina Platerów, powiat łosicki)
that Tomek Kołodziejczuk ran from 2007 to 2011 on Joomla 1.0. The original host is gone; this
rebuild comes from Internet Archive Wayback Machine captures.

- Live: https://itstomekk.github.io/chlopkow-pl/ (GitHub Pages, `main` / `docs/`)
- Repo: https://github.com/itstomekk/chlopkow-pl

## What is in it

- `docs/` the published site: articles (`a/<old Joomla id>.html`), section pages, photo gallery,
  guestbook, the "Czy wiesz, że..." facts, and an all-articles index. Images are kept under
  `docs/media/` at their original site paths.
- `data/` reusable JSON: `articles.json` (plain text + metadata + Wayback link), `czy-wiesz.json`,
  `gallery.json`. Prepared as source material for the CHŁOPKÓW LEGENDS knowledge base; this
  release does not modify the game runtime or publish a game build.
- `build.py` regenerates `docs/` and `data/` from the crawl archive.
- `safe_html.py` strips contact details and active archived HTML.
- `assets/` stylesheet and favicon source.

Current recovery: 175 article records, 41 full-view captures and 134 listing intros, 60 guestbook
entries, 22 historical fact-module variants, 219 photo captions across six gallery categories.
No original photo files have been recovered. Some full-view pages were image-only; their missing
images are not reconstructed or replaced with invented content. Original copyright remains with
its authors; the MIT license in `LICENSE` covers the code only, not recovered articles, data or future image recoveries.

## Rebuild

The private crawl stays outside this repository at
`C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie/references/chlopkow-pl-archiwum/`.
A supplementary recovery snapshot preserves the original crawl and adds recovered full articles.
Use that merged snapshot to avoid reverting to the earlier intro-only versions:

`python build.py --archive C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie/references/chlopkow-pl-archiwum/recovery-20261018`

Then run `python -m unittest test_privacy -v` and `python validate.py` (the browser smoke test
requires an installed Playwright Firefox). The generated site needs no JavaScript or dependencies
on GitHub Pages. Source timestamps and listing-only coverage are retained per article.

## Rules

- Publish what the old public site showed, but **strip e-mail addresses, phone and Gadu-Gadu numbers**
  (Tomek, 2026-10-17). `build.py` does this in `scrub()`; check new content with a grep before pushing.
- The contact form and the "submit article" form are not rebuilt.
- Text that only survived as an intro on a listing page is marked as such on the article page.
