"""Indexability and discovery checks without changing visible page content."""
from html.parser import HTMLParser
import unittest
import xml.etree.ElementTree as ET
from app import app


class PageTags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class SeoTests(unittest.TestCase):
    def test_homepage_metadata_and_preserved_semantics(self):
        response = app.test_client().get('/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        tags = PageTags(html).tags
        self.assertIn('<title>Email Check · Phishing detector</title>', html)
        descriptions = [a['content'] for t, a in tags if t == 'meta' and a.get('name') == 'description']
        self.assertEqual(descriptions, ['Check suspicious emails with our free AI phishing detector. Identify potential scam warning signs, understand the results, and get simple safety advice.'])
        canonicals = [a['href'] for t, a in tags if t == 'link' and a.get('rel') == 'canonical']
        self.assertEqual(canonicals, ['https://email-check-lrw9.onrender.com/'])
        self.assertEqual(sum(t == 'h1' for t, a in tags), 1)
        self.assertIn('<h1 id="hero-title">Not Sure If an<br>Email Is <span>Safe?</span></h1>', html)
        self.assertIn(('img', {'src': '/static/ai-assistant.svg', 'alt': '', 'width': '640', 'height': '620', 'fetchpriority': 'high'}), tags)

    def test_sitemap_has_only_public_homepage(self):
        with app.test_client().get('/sitemap.xml', follow_redirects=False) as response:
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('Location', response.headers)
            self.assertEqual(response.mimetype, 'application/xml')
            root = ET.fromstring(response.data)
            ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
            self.assertEqual(root.tag, ns + 'urlset')
            self.assertEqual([node.text for node in root.iter(ns + 'loc')], ['https://email-check-lrw9.onrender.com/'])
            self.assertEqual(len(root), 1)

    def test_no_indexing_blocks(self):
        client = app.test_client()
        response = client.get('/')
        self.assertNotIn('noindex', response.headers.get('X-Robots-Tag', '').lower())
        self.assertNotIn('none', response.headers.get('X-Robots-Tag', '').lower())
        for tag, attrs in PageTags(response.get_data(as_text=True)).tags:
            if tag == 'meta' and attrs.get('name', '').lower() in ('robots', 'googlebot'):
                self.assertNotIn('noindex', attrs.get('content', '').lower())
                self.assertNotIn('none', attrs.get('content', '').lower())
        robots = client.get('/robots.txt', follow_redirects=False)
        # No robots file means there are no robots.txt crawl restrictions.
        self.assertEqual(robots.status_code, 404)
