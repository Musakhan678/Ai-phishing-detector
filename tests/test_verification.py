"""The permanent Search Console URL must serve the exact file, not redirect."""
import unittest
from app import app


class VerificationTests(unittest.TestCase):
    def test_root_verification_file(self):
        with app.test_client().get('/googleba5025845859c5bf.html', follow_redirects=False) as response:
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('Location', response.headers)
            self.assertEqual(response.mimetype, 'text/html')
            self.assertEqual(response.data, b'google-site-verification: googleba5025845859c5bf.html')
