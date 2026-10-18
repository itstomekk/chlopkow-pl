"""Release gates: archived HTML must be inert and contact-free."""
import unittest
import build


class PrivacyTests(unittest.TestCase):
    def test_full_article_keeps_text_after_nested_table(self):
        source = ('<td class="contentheading">Title</td><td class="createdate">01.01.2009.</td>'
                  '<tr><td valign="top" colspan="2">Before<table><tr><td>Nested</td></tr></table>'
                  '<p>After</p></td></tr></table>')
        article = build.parse_article(source)
        self.assertIn('After', article['body_html'])

    def test_contacts_removed_but_dates_and_years_preserved(self):
        value = 'Dzieje 1797-1890, 05.10.2009. Tel. +48 501 234 567; e-mail abc@example.invalid'
        safe = build.scrub(value)
        self.assertIn('1797-1890', safe)
        self.assertIn('05.10.2009', safe)
        self.assertNotIn('501', safe)
        self.assertNotIn('abc@', safe)

    def test_html_sanitizer_decodes_contacts_and_removes_active_content(self):
        from safe_html import sanitize_html
        source = ('<p onclick="alert(1)">Mail: abc&#64;example.invalid'
                  '<a href="mailto:abc@example.invalid">napisz</a>'
                  '<a href="tel:501234567">501234567</a>'
                  '<a href="javascript:alert(1)">link</a>'
                  '<script>alert(1)</script><iframe src="https://example.invalid"></iframe></p>')
        safe = sanitize_html(source)
        for forbidden in ('abc@', 'mailto:', 'tel:', '501234567', 'onclick', 'javascript:', '<script', '<iframe'):
            self.assertNotIn(forbidden, safe)
        self.assertIn('napisz', safe)

    def test_html_links_do_not_get_corrupted_by_phone_redaction(self):
        from safe_html import sanitize_html
        source = '<a href="https://web.archive.org/web/20100115114032/http://chlopkow.pl/content/view/214/1/">10.01.2010</a>'
        self.assertEqual(sanitize_html(source), source)


if __name__ == '__main__':
    unittest.main()
