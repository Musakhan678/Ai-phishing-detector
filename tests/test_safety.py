"""Advice checks are independent from the model and report literal wording."""
import json
import unittest
from unittest.mock import patch
from app import app, BASE_DIR
from safety import detect_warning_signs, build_safety_advice


class SafetyTests(unittest.TestCase):
    def test_calm_and_caution_advice(self):
        calm = build_safety_advice(0, [])
        self.assertEqual(calm['mode'], 'calm')
        self.assertIn('reassuring', calm['introduction'])
        self.assertIn("hasn't been verified as safe", calm['introduction'])
        self.assertEqual(calm['steps'], [
            'You can review the email as usual, but be cautious about unexpected requests.',
            "If you're asked for money, passwords, or personal details, verify the sender first.",
            'If something seems unusual, contact the sender through a trusted channel.'])
        for warnings in [[], detect_warning_signs('Please send your password immediately.')]:
            caution = build_safety_advice(1, warnings)
            self.assertEqual(caution['mode'], 'caution')
            self.assertNotIn('reassuring', caution['introduction'])
            self.assertEqual(caution['steps'], [
                "Don't click unexpected links or open unfamiliar attachments.",
                "Don't share passwords, verification codes, or financial details.",
                'Contact the organization through its official website or a trusted phone number.'])

    def test_legitimate_with_risk_gets_specific_caution(self):
        examples = [
            ('Please send your password.', 'password'),
            ('Hi can you wire me $3000 immediately', 'money'),
            ('Your account has been suspended.', 'account restriction'),
            ('Act now.', 'rush you'),
        ]
        for email, expected_text in examples:
            with self.subTest(email=email):
                advice = build_safety_advice(0, detect_warning_signs(email))
                self.assertEqual(advice['mode'], 'warning_exception')
                self.assertIn('separate text checks', advice['introduction'])
                self.assertNotIn('reassuring', advice['introduction'])
                self.assertIn(expected_text, advice['steps'][0])
                self.assertEqual(len(advice['steps']), 3)

    def test_real_endpoint_advice_states_and_original_labels(self):
        client = app.test_client()
        examples = json.loads((BASE_DIR / 'tests/example_emails.json').read_text())
        for email, label, mode in [
            (examples['school_homework'], 0, 'calm'),
            (examples['prize_scam'], 1, 'caution'),
            (examples['order_confirmation'], 1, 'caution'),
            ('Hi this is samuel can you wire me $3000', 0, 'warning_exception'),
        ]:
            response = client.post('/predict', json={'email': email})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['prediction'], label)
            self.assertEqual(response.json['safety_advice']['mode'], mode)
            self.assertEqual(len(response.json['safety_advice']['steps']), 3)

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
