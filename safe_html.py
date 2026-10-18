"""Keep archived rich text inert; strip contact details only in visible text."""
import html
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

EMAIL = re.compile(r"[\w.+-]+\s*(?:@|\(at\)|\[at\])\s*[\w-]+(?:\.[\w-]+)+", re.I)
PHONE = re.compile(r"(?<!\d)(?:(?:\+|00)48[\s.-]?)?(?:\(?0?\d{2}\)?[\s.-]?)?\d{3}[\s.-]\d{2,3}[\s.-]\d{2,3}(?!\d)|(?<!\d)\d{9}(?!\d)")
PHONE_CTX = re.compile(r"(?i)\b(tel\.?|telefon\w*|kom\.?|komórk\w*|fax|gg|gadu[- ]?gadu)\s*[:.]?\s*[\d\s()+./-]{5,}")


def scrub_text(value):
    value = html.unescape(value)
    value = EMAIL.sub('[e-mail usunięty]', value)
    value = PHONE_CTX.sub(lambda m: m.group(1) + ' [numer usunięty]', value)
    return PHONE.sub('[numer usunięty]', value)


class SafeHTML(HTMLParser):
    allowed = set('p div span br hr a img b strong i em u s del sup sub h1 h2 h3 h4 h5 h6 ul ol li blockquote pre code table thead tbody tfoot tr td th caption'.split())
    blocked = set('script style iframe object embed form noscript svg math template'.split())
    void = {'br', 'hr', 'img'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.suppressed = []

    def handle_starttag(self, tag, attrs):
        if self.suppressed:
            if tag in self.blocked and tag != 'embed':
                self.suppressed.append(tag)
            return
        if tag in self.blocked:
            if tag != 'embed':
                self.suppressed.append(tag)
            return
        if tag not in self.allowed:
            return
        keep = []
        for name, val in attrs:
            if val is None:
                continue
            if name in ('href', 'src') and ((tag == 'a' and name == 'href') or (tag == 'img' and name == 'src')):
                decoded = unquote(html.unescape(val))
                scheme = urlsplit(val).scheme.lower()
                if scheme not in ('', 'http', 'https') or any(c in val for c in '\r\n\t'):
                    continue
                if EMAIL.search(decoded) or re.search(r'(?i)(?:mailto:|tel:|[?&](?:email|phone|gg)=)', decoded):
                    continue
                keep.append((name, val))
            elif name in ('alt', 'title'):
                keep.append((name, scrub_text(val)))
            elif name in ('colspan', 'rowspan', 'width', 'height') and val.isdigit() and int(val) <= 2000:
                keep.append((name, val))
        if tag == 'img' and not any(k == 'src' for k, _ in keep):
            return
        self.out.append('<' + tag + ''.join(f' {k}="{html.escape(v, quote=True)}"' for k, v in keep) + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.suppressed:
            if tag == self.suppressed[-1]:
                self.suppressed.pop()
            return
        if tag in self.allowed and tag not in self.void:
            self.out.append(f'</{tag}>')

    def handle_data(self, data):
        if not self.suppressed:
            self.out.append(html.escape(scrub_text(data), quote=False))


def sanitize_html(value):
    parser = SafeHTML()
    parser.feed(value)
    parser.close()
    return ''.join(parser.out)
