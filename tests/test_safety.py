"""Advice checks are independent from the model and report literal wording."""
import json
import unittest
from unittest.mock import patch
from app import app, BASE_DIR
from safety import detect_warning_signs


class SafetyTests(unittest.TestCase):
    def test_exact_email_advice(self):
        examples = json.loads((BASE_DIR / 'tests/example_emails.json').read_text())
        expected = {'school_homework': set(), 'order_confirmation': set(),
                    'bank_impersonation': {'secrets', 'account', 'pressure'},
                    'prize_scam': {'money', 'pressure'}}
        for name, email in examples.items():
            with self.subTest(name=name):
                warnings = detect_warning_signs(email)
                self.assertEqual({w['code'] for w in warnings}, expected[name])
                for warning in warnings:
                    self.assertIn(warning['evidence'], email)

    def test_literal_requests_and_negated_safety_advice(self):
        for email in ['Never share your password.', 'Do not send bank details.',
                      "Don't provide your verification code.", 'My package arrives tomorrow.',
                      'The homework deadline is tomorrow.']:
            self.assertEqual(detect_warning_signs(email), [])
        self.assertIn('secrets', {w['code'] for w in detect_warning_signs('Please enter your verification code.')})
        self.assertIn('money', {w['code'] for w in detect_warning_signs('Hi can you wire me $3000')})
        self.assertEqual(detect_warning_signs('Provide some answers. My password is private.'), [])

    def test_advice_cannot_change_prediction(self):
        client = app.test_client()
        email = 'Please confirm your password immediately.'
        before = client.post('/predict', json={'email': email}).json
        with patch('app.detect_warning_signs', return_value=[]):
            after = client.post('/predict', json={'email': email}).json
        self.assertEqual(before['prediction'], after['prediction'])
        self.assertEqual(before['explanation'], after['explanation'])
        self.assertTrue(before['warning_signs'])
        self.assertEqual(after['warning_signs'], [])

    def test_accessible_disclosures_and_labels(self):
        html = app.test_client().get('/').get_data(as_text=True)
        self.assertIn('<summary>Learn how the AI made its decision</summary>', html)
        self.assertIn('<summary>Technical details</summary>', html)
        self.assertIn('id="ai-explanation">', html)
        self.assertIn('id="prediction-guide">', html)
        self.assertIn('id="result-title" tabindex="-1"', html)
        self.assertIn('role="status" aria-live="polite"', html)
        self.assertIn('What should you watch out for?', html)
        self.assertIn('What should you do?', html)
