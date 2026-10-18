"""Validate generated Pages files and render desktop/mobile without external requests."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import collections, functools, http.server, json, re, threading
from safe_html import EMAIL, PHONE

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'docs'


class Audit(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.refs = []
        self.bad = []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'iframe', 'object', 'form', 'embed'}:
            self.bad.append(tag)
        for key, val in attrs:
            if key.startswith('on'):
                self.bad.append(key)
            if key in ('href', 'src') and val:
                self.refs.append(val)
                if urlsplit(val).scheme.lower() in ('javascript', 'mailto', 'tel', 'vbscript', 'file') or EMAIL.search(unquote(val)):
                    self.bad.append('unsafe URL')

    def handle_data(self, data):
        self.text.append(data)


def validate():
    errors = []
    pages = list(DOCS.rglob('*.html'))
    for file in pages:
        parser = Audit()
        parser.feed(file.read_text(encoding='utf-8'))
        text = ''.join(parser.text)
        if EMAIL.search(text) or PHONE.search(text):
            errors.append((str(file.relative_to(DOCS)), 'contact candidate'))
        for ref in parser.refs:
            parts = urlsplit(ref)
            if not parts.scheme and not parts.netloc and parts.path:
                target = (file.parent / unquote(parts.path)).resolve()
                if not target.is_file():
                    errors.append((str(file.relative_to(DOCS)), 'missing ' + ref))
        if parser.bad:
            errors.append((str(file.relative_to(DOCS)), parser.bad))
    for file in (ROOT / 'data').glob('*.json'):
        json.loads(file.read_text(encoding='utf-8'))
    articles = json.loads((ROOT / 'data/articles.json').read_text(encoding='utf-8'))
    for a in articles:
        assert a['wayback'], a['id']
        assert (DOCS / 'a' / f'{a["id"]}.html').is_file()
        for k in ('title', 'author', 'text'):
            assert not EMAIL.search(a[k]), (a['id'], k, 'email')
    print('HTML pages:', len(pages), 'articles:', len(articles), 'full views:', sum(not a['intro_only'] for a in articles))
    print('Validation errors:', errors[:15], 'total', len(errors))
    assert not errors, 'release gate failed'
    return articles


def browser():
    from playwright.sync_api import sync_playwright
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/'
    out = Path(r'C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\chlopkow-recovery')
    out.mkdir(exist_ok=True, parents=True)
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        issues = []
        page.on('pageerror', lambda e: issues.append(str(e)))
        page.route('**/*', lambda r: r.continue_() if r.request.url.startswith(url) else r.abort())
        page.goto(url)
        page.screenshot(path=str(out / 'desktop.png'), full_page=True)
        page.get_by_role('link', name='Zarys historii', exact=True).click()
        assert page.locator('main').inner_text().find('Historia Parafii') >= 0
        page.goto(url + 'a/205.html')
        assert 'popówkę' in page.locator('main').inner_text()
        page.goto(url + 'galeria.html')
        assert 'nie udało się odzyskać plików' in page.locator('main').inner_text()
        page.goto(url + 'ksiega-gosci.html')
        assert page.locator('.gb').count() == 60
        page.set_viewport_size({'width': 390, 'height': 844})
        page.goto(url)
        page.screenshot(path=str(out / 'mobile.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2')
        assert not issues, issues
        print('Firefox desktop/mobile, navigation, history article, gallery and 60 guestbook entries: PASS')
        browser.close()
    server.shutdown()


if __name__ == '__main__':
    validate()
    browser()
