"""Build the static chlopkow.pl rebuild (GitHub Pages, docs/) from the Wayback crawl.

Input: the private crawl archive made by
  C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie/gen/wayback/crawl_chlopkow_pl.py
  (state.json + raw/ under arek-w-chlopkowie/references/chlopkow-pl-archiwum/)
Output: docs/ (published site) and data/ (JSON for reuse, e.g. by the CHŁOPKÓW LEGENDS game).

Privacy rule (Tomek, 2026-10-17): publish everything the old public site showed, but strip
e-mail addresses, phone numbers and Gadu-Gadu numbers. The contact form page is not rebuilt.

Usage: python build.py [--archive PATH]
Stdlib only.
"""
import argparse, html, json, os, re, shutil, urllib.parse
from collections import defaultdict
import hashlib
from safe_html import scrub_text, sanitize_html

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ARC = r"C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie\references\chlopkow-pl-archiwum"
DOCS = os.path.join(HERE, "docs")
DATA = os.path.join(HERE, "data")

SECTIONS = [  # (match in listing url, slug, name) — the old left menu
    ("/blogsection/1/", "wiesci", "Wieś-ci"),
    ("/blogsection/0/", "artykuly", "Artykuły - pozostałe"),
    ("/category/7/23/", "gmina", "Gmina Platerów"),
    ("/blogsection/8/", "regionalne", "Regionalne"),
    ("/category/7/20/", "droga-krzyzowa", "Droga Krzyżowa"),
    ("/blogcategory/22/", "internet", "Internet a region"),
    ("com_frontpage", "strona-glowna", "Strona Wsi"),
]
MENU_PAGES = [(50, "Ogólne info o Chłopkowie"), (53, "Zarys historii"), (55, "Parafia"), (54, "Informacje"),
              (58, "Legenda o wiedźmie"), (85, "Mapa"), (87, "Satelita"), (162, "PKS")]

# ---------------------------------------------------------------- privacy
EMAIL = re.compile(r"[\w.+-]+\s*(?:@|\(at\)|\[at\]|&#64;)\s*[\w-]+(?:\.[\w-]+)+", re.I)
PHONE = re.compile(r"(?:(?:\+|00)48[\s.-]?)?(?:\(?0?\d{2}\)?[\s.-]?)?\d{3}[\s.-]\d{2,3}[\s.-]\d{2,3}(?!\d)|(?<!\d)\d{9}(?!\d)")
PHONE_CTX = re.compile(r"(?i)(tel\.?|telefon\w*|kom\.?|komórk\w*|fax|gg|gadu[- ]?gadu)\s*[:.]?\s*[\d\s()+./-]{5,}")


def scrub(s):
    return scrub_text(s)


# ---------------------------------------------------------------- helpers
def decode(data):
    m = re.search(rb"charset=([\w-]+)", data[:3000], re.I)
    enc = (m.group(1).decode() if m else "iso-8859-2").lower()
    if enc in ("iso-8859-1", "latin1"):
        enc = "iso-8859-2"
    try:
        return data.decode(enc, errors="replace").replace('\r', '')
    except LookupError:
        return data.decode("iso-8859-2", errors="replace").replace('\r', '')


def text_of(h):
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</li>|</h\d>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h).replace("\xa0", " ")
    h = re.sub(r"[ \t\r]+", " ", h)
    h = re.sub(r" *\n *", "\n", h)
    return re.sub(r"\n{3,}", "\n\n", h).strip()


def norm(u, base="http://chlopkow.pl/"):
    try:
        c = urllib.parse.urljoin(base, html.unescape(u.strip()))
    except ValueError:
        return None
    c = re.sub(r"^https?://web\.archive\.org/web/\d+[a-z_]*/", "", c)
    if not c.startswith("http"):
        c = "http://" + c
    return re.sub(r"^https?://(www\.)?chlopkow\.pl", "http://chlopkow.pl", c)


def article_id(url):
    m = re.search(r"/content/view/(\d+)/", url)
    if not m and "com_content" in url and "task=view" in url:
        m = re.search(r"[?&]id=(\d+)", url)
    return int(m.group(1)) if m else None


def date_key(d):
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", d or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else "0000-00-00"


def parse_article(t):
    mh = re.search(r'class="contentheading"[^>]*>(.*?)</td>', t, re.S)
    if not mh:
        return None
    rest = t[mh.end():]
    author = re.search(r"Wpisał:\s*(.*?)</span>", rest, re.S)
    date = re.search(r'class="createdate"[^>]*>(.*?)</td>', rest, re.S)
    start = date.end() if date else 0
    mb = re.search(r'<td valign="top" colspan="2">', rest[start:], re.S)
    body = ''
    if mb:
        tail = rest[start:][mb.end():]
        depth = 1
        for cell in re.finditer(r'</?td\b[^>]*>', tail, re.I):
            depth += -1 if cell.group().startswith('</') else 1
            if depth == 0:
                body = tail[:cell.start()].strip()
                break
    return {"title": text_of(mh.group(1)), "author": text_of(author.group(1)) if author else "",
            "date": text_of(date.group(1)).rstrip(".") if date else "", "body_html": body}


def parse_listing(t):
    out = []
    for m in re.finditer(r'class="contentheading"[^>]*>(.*?)</td>(.*?)(?=class="contentheading"|<span class="article_seperator"|$)', t, re.S):
        chunk = m.group(2)
        link = re.search(r'href="([^"]*(?:/content/view/\d+/|task=view&amp;id=\d+)[^"]*)"', m.group(1) + chunk)
        aid = article_id(html.unescape(link.group(1))) if link else None
        date = re.search(r'class="createdate"[^>]*>(.*?)</td>', chunk, re.S)
        author = re.search(r"Wpisał:\s*(.*?)</span>", chunk, re.S)
        body = re.search(r'<td valign="top" colspan="2">(.*?)</td>', chunk[date.end():] if date else chunk, re.S)
        out.append({"id": aid, "title": text_of(m.group(1)), "date": text_of(date.group(1)).rstrip(".") if date else "",
                    "author": text_of(author.group(1)) if author else "", "intro_html": body.group(1).strip() if body else ""})
    return out


def parse_guestbook(t):
    out = {}
    for m in re.finditer(r"<a name='gb(\d+)'></a><b>(.*?)</b>(.*?)</td>\s*<td[^>]*>\s*<span class='small'>Dodany:\s*(.*?)<hr></span>(.*?)</td>\s*</tr>", t, re.S):
        gid, name, extra, added, msg = m.groups()
        frm = re.search(r"Skąd:</b>\s*\(<em>(.*?)</em>\)", extra, re.S)
        out[int(gid)] = {"id": int(gid), "name": text_of(name), "from": text_of(frm.group(1)) if frm else "",
                         "added": text_of(added), "html": msg.strip()}
    return out


def parse_gallery_category(t):
    cat = re.search(r'<td colspan="4" class="sectiontableheader"[^>]*>\s*<div align="center">\s*(.*?)\s*</div>', t, re.S)
    if not cat:
        return None, []
    items = []
    for m in re.finditer(r'<a href="([^"]*img_pictures/[^"]+)"[^>]*>\s*<img src="([^"]+)"[^>]*alt="([^"]*)"[^>]*/>\s*</a>\s*<br />\s*<b>(.*?)</b>', t, re.S):
        items.append({"picture": norm(m.group(1)), "thumb": norm(m.group(2)), "title": text_of(m.group(4)) or text_of(m.group(3))})
    return text_of(cat.group(1)), items


def czy_wiesz(t):
    return [text_of(m.group(1)) for m in re.finditer(r"<h3>\s*Czy wiesz, że\.\.\.\s*</h3>\s*(.*?)</div>", t, re.S) if text_of(m.group(1))]


# ---------------------------------------------------------------- build
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default=DEFAULT_ARC)
    a = ap.parse_args()
    arc, raw = a.archive, os.path.join(a.archive, "raw")
    st = json.load(open(os.path.join(arc, "state.json"), encoding="utf-8"))
    recs = [r for r in st["done"].values() if r.get("status") == 200 and r.get("file")]

    if os.path.isdir(DOCS):
        for n in os.listdir(DOCS):
            if n not in ("CNAME",):
                p = os.path.join(DOCS, n)
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for d in ("a", "media"):
        os.makedirs(os.path.join(DOCS, d), exist_ok=True)
    os.makedirs(DATA, exist_ok=True)

    # images: keep the original site path under media/
    img_local = {}
    for r in recs:
        if r["kind"] != "image":
            continue
        u = r["url"]
        if u in img_local:
            continue
        path = urllib.parse.unquote(urllib.parse.urlsplit(u).path).lstrip("/")
        path = re.sub(r"[^\w./-]", "_", path)
        if path.startswith("components/com_akobook/") or "/templates/" in u:
            continue
        dst = os.path.join(DOCS, "media", path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(raw, r["file"]), dst)
        img_local[u] = "media/" + path

    articles, intros, facts, guest = {}, defaultdict(list), defaultdict(set), {}
    section_of, gallery = defaultdict(set), defaultdict(dict)
    for r in recs:
        if r["kind"] != "page":
            continue
        t = decode(open(os.path.join(raw, r["file"]), "rb").read())
        y = (r["ts"] or "")[:4]
        for f in czy_wiesz(t):
            facts[f].add(y)
        u = r["url"]
        if "com_akobook" in u:
            guest.update(parse_guestbook(t))
            continue
        if "com_ponygallery" in u:
            cat, items = parse_gallery_category(t)
            if cat:
                for it in items:
                    gallery[cat].setdefault(it["picture"], it)
            continue
        aid = article_id(u)
        if aid is not None:
            art = parse_article(t)
            if art and art["body_html"]:
                art.update(id=aid, url=u, ts=r["ts"])
                prev = articles.get(aid)
                if not prev or len(text_of(art["body_html"])) > len(text_of(prev["body_html"])):
                    articles[aid] = art
                continue
        for it in parse_listing(t):
            if it["id"]:
                it["ts"] = r["ts"]
                it["source_url"] = u
                intros[it["id"]].append(it)
                for key, slug, _ in SECTIONS:
                    if key in u:
                        section_of[it["id"]].add(slug)

    for aid, lst in intros.items():
        if aid not in articles:
            best = max(lst, key=lambda x: len(x["intro_html"]))
            articles[aid] = {"id": aid, "title": best["title"], "author": best["author"], "date": best["date"],
                             "body_html": best["intro_html"], "url": None, "listing_url": best["source_url"], "ts": best["ts"], "intro_only": True}

    for art in articles.values():
        for field in ('title', 'author', 'date'):
            art[field] = scrub(art[field])
    facts = {scrub(f): years for f, years in facts.items()}

    def localize(h, base, prefix):
        def img(m):
            loc = img_local.get(norm(m.group(2), base) or "")
            return f'{m.group(1)}"{prefix}{loc}"' if loc else f'{m.group(1)}"data:," data-old-src="{html.escape(m.group(2))}"'
        h = re.sub(r"(?is)<script\b.*?</script>|<noscript\b.*?</noscript>|<iframe\b.*?</iframe>|<object\b.*?</object>", "", h)
        h = re.sub(r'(<img[^>]*?\bsrc=)["\']?([^"\'\s>]+)["\']?', img, h, flags=re.I)

        def link(m):
            n = norm(m.group(1), base) or ""
            aid = article_id(n)
            if aid in articles:
                return f'href="{prefix}a/{aid}.html"'
            if n in img_local:
                return f'href="{prefix}{img_local[n]}"'
            if n.startswith("http://chlopkow.pl"):
                return f'href="https://web.archive.org/web/2010/{n}"'
            return m.group(0)
        h = re.sub(r'href="([^"]+)"', link, h)
        return sanitize_html(h)

    # ---------------- templates
    side = "".join(f'<li><a href="{{p}}a/{i}.html">{html.escape(n)}</a></li>' for i, n in MENU_PAGES if i in articles)
    secs = "".join(f'<li><a href="{{p}}dzial-{s}.html">{html.escape(n)}</a></li>' for _, s, n in SECTIONS if s != "strona-glowna")
    fact_list = sorted(facts)

    def page(title, body, p=""):
        menu = (f'<ul><li><a href="{p}index.html">Strona Wsi</a></li>{secs.format(p=p)}'
                f'<li><a href="{p}galeria.html">Galeria zdjęć</a></li><li><a href="{p}ksiega-gosci.html">Księga Gości</a></li>'
                f'<li><a href="{p}czy-wiesz.html">Czy wiesz, że...</a></li><li><a href="{p}archiwum.html">Wszystkie artykuły</a></li></ul>'
                f'<h3>O Chłopkowie</h3><ul>{side.format(p=p)}</ul>')
        fact_index = int(hashlib.sha256(title.encode('utf-8')).hexdigest(), 16)
        fact = html.escape(fact_list[fact_index % len(fact_list)]) if fact_list else ""
        return f"""<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · Chłopków.pl</title><link rel="stylesheet" href="{p}style.css"><link rel="icon" href="{p}favicon.svg"></head><body>
<header><a href="{p}index.html"><span class="logo">Chłopków.pl</span><span class="tag">nowe oblicze Chłopkowa · strona wsi</span></a></header>
<div class="wrap"><nav>{menu}</nav><main>{body}</main><aside><h3>Czy wiesz, że...</h3><p>{fact}</p>
<h3>O archiwum</h3><p>Strona wsi Chłopków prowadzona przez Tomka Kołodziejczuka w latach 2007–2011, odtworzona w 2026 z kopii w <a href="https://web.archive.org/web/2010/http://www.chlopkow.pl/">Wayback Machine</a>. Adresy e-mail i numery telefonów usunięto.</p></aside></div>
<footer>Chłopków, gmina Platerów, powiat łosicki · archiwum 2007–2011</footer></body></html>"""

    def teaser(a, p=""):
        intro = text_of(a["body_html"])[:280]
        return (f'<article class="teaser"><h2><a href="{p}a/{a["id"]}.html">{html.escape(a["title"])}</a></h2>'
                f'<p class="meta">{html.escape(a["author"])} · {html.escape(a["date"])}</p><p>{html.escape(scrub(intro))}…</p></article>')

    order = sorted(articles.values(), key=lambda x: (date_key(x["date"]), x["id"]), reverse=True)
    for art in order:
        src = (f'<a href="https://web.archive.org/web/{art["ts"]}/{art["url"]}">kopia z {art["ts"][:4]}-{art["ts"][4:6]}-{art["ts"][6:8]}</a>'
               if art.get("url") else f'<a href="https://web.archive.org/web/{art["ts"]}/{art["listing_url"]}">wstęp na stronie zbiorczej</a>')
        note = '<p class="note">Z tego artykułu w archiwum zachował się tylko wstęp.</p>' if art.get("intro_only") else ""
        body = (f'<article><h1>{html.escape(art["title"])}</h1><p class="meta">Wpisał: {html.escape(art["author"])} · {html.escape(art["date"])} · {src}</p>'
                f'{note}<div class="body">{localize(art["body_html"], art.get("url") or "http://chlopkow.pl/", "../")}</div></article>')
        open(os.path.join(DOCS, "a", f'{art["id"]}.html'), "w", encoding="utf-8").write(page(art["title"], body, "../"))

    dated = [x for x in order if date_key(x["date"]) != "0000-00-00"]
    open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8").write(page("Strona Wsi",
        '<p class="note">Archiwum strony wsi Chłopków z lat 2007–2011. '
        f'{len(order)} artykułów, {len(img_local)} odzyskanych obrazów, {len(guest)} wpisów w księdze gości. '
        f'Zachowano też opisy {sum(len(v) for v in gallery.values())} pozycji galerii.</p>'
        + "".join(teaser(x) for x in dated[:15]) + '<p><a href="archiwum.html">Wszystkie artykuły »</a></p>'))

    by_year = defaultdict(list)
    for x in order:
        by_year[date_key(x["date"])[:4]].append(x)
    arch = []
    for y in sorted(by_year, reverse=True):
        arch.append(f"<h2>{y if y != '0000' else 'Bez daty'}</h2><ul class='list'>")
        arch += [f'<li><a href="a/{x["id"]}.html">{html.escape(x["title"])}</a> <span class="meta">{html.escape(x["date"])}</span>'
                 f'{" <small>(wstęp)</small>" if x.get("intro_only") else ""}</li>' for x in by_year[y]]
        arch.append("</ul>")
    open(os.path.join(DOCS, "archiwum.html"), "w", encoding="utf-8").write(page("Wszystkie artykuły", "<h1>Wszystkie artykuły</h1>" + "".join(arch)))

    for _, slug, name in SECTIONS:
        if slug == "strona-glowna":
            continue
        lst = [x for x in order if slug in section_of.get(x["id"], ())]
        open(os.path.join(DOCS, f"dzial-{slug}.html"), "w", encoding="utf-8").write(
            page(name, f"<h1>{html.escape(name)}</h1>" + ("".join(teaser(x) for x in lst) or "<p>Brak zachowanych artykułów.</p>")))

    # gallery
    g = []
    shown = set()
    for cat in sorted(gallery):
        items = [it for it in gallery[cat].values() if img_local.get(it["picture"]) or img_local.get(it["thumb"])]
        if not items:
            g.append(f'<h2>{html.escape(scrub(cat))}</h2><p class="note">Zachowały się opisy zdjęć, ale nie udało się odzyskać plików.</p><ul class="list">')
            for it in gallery[cat].values():
                label = html.escape(scrub(it['title']))
                g.append(f'<li>{label}</li>')
            g.append('</ul>')
            continue
        g.append(f"<h2>{html.escape(cat)} <small>({len(items)})</small></h2><div class='grid'>")
        for it in items:
            big = img_local.get(it["picture"]) or img_local.get(it["thumb"])
            th = img_local.get(it["thumb"]) or big
            shown.update({it["picture"], it["thumb"]})
            g.append(f'<figure><a href="{big}"><img loading="lazy" src="{th}" alt="{html.escape(it["title"])}"></a><figcaption>{html.escape(it["title"])}</figcaption></figure>')
        g.append("</div>")
    rest = [(u, l) for u, l in sorted(img_local.items()) if u not in shown and "img_thumbnails" not in u and "/images/stories/" in u]
    if rest:
        g.append(f"<h2>Inne zdjęcia ze strony <small>({len(rest)})</small></h2><div class='grid'>")
        g += [f'<figure><a href="{l}"><img loading="lazy" src="{l}" alt=""></a></figure>' for u, l in rest]
        g.append("</div>")
    open(os.path.join(DOCS, "galeria.html"), "w", encoding="utf-8").write(page("Galeria zdjęć", "<h1>Galeria zdjęć</h1>" + "".join(g)))

    gb = [f'<div class="gb"><p class="meta"><b>{html.escape(scrub(e["name"]))}</b>{(" · " + html.escape(scrub(e["from"]))) if e["from"] else ""} · {html.escape(e["added"])}</p>'
          f'<p>{localize(e["html"], "http://chlopkow.pl/", "")}</p></div>' for e in sorted(guest.values(), key=lambda e: -e["id"])]
    open(os.path.join(DOCS, "ksiega-gosci.html"), "w", encoding="utf-8").write(
        page("Księga Gości", f"<h1>Księga Gości</h1><p class='meta'>{len(guest)} zachowanych wpisów. Nowych wpisów już nie dodamy.</p>" + "".join(gb)))

    open(os.path.join(DOCS, "czy-wiesz.html"), "w", encoding="utf-8").write(page("Czy wiesz, że...",
        "<h1>Czy wiesz, że...</h1><ul class='list'>" + "".join(f"<li>{html.escape(f)} <span class='meta'>{', '.join(sorted(facts[f]))}</span></li>" for f in fact_list) + "</ul>"))

    shutil.copyfile(os.path.join(HERE, "assets", "style.css"), os.path.join(DOCS, "style.css"))
    shutil.copyfile(os.path.join(HERE, "assets", "favicon.svg"), os.path.join(DOCS, "favicon.svg"))
    open(os.path.join(DOCS, ".nojekyll"), "w").close()

    # data for reuse (scrubbed)
    json.dump([{"id": x["id"], "title": x["title"], "author": x["author"], "date": x["date"], "sections": sorted(section_of.get(x["id"], ())),
                "intro_only": bool(x.get("intro_only")), "wayback": f'https://web.archive.org/web/{x["ts"]}/{x.get("url") or x.get("listing_url")}',
                "text": scrub(text_of(x["body_html"]))} for x in order],
              open(os.path.join(DATA, "articles.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump([{"fact": f, "years": sorted(facts[f])} for f in fact_list], open(os.path.join(DATA, "czy-wiesz.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({c: list(v.values()) for c, v in gallery.items()}, open(os.path.join(DATA, "gallery.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"articles={len(order)} full={sum(1 for x in order if not x.get('intro_only'))} images={len(img_local)} "
          f"gallery_cats={len(gallery)} gallery_items={sum(len(v) for v in gallery.values())} guestbook={len(guest)} facts={len(facts)}")


if __name__ == "__main__":
    main()
