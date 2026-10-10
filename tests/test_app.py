"""Run with python -m unittest discover -s tests -v."""
import hashlib
import unittest
from unittest.mock import patch
from app import app, clean_text, model, tfidf, BASE_DIR, explain_features


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_cleaning_matches_training(self):
        self.assertEqual(clean_text(' <b>HELLO!</b>  Visit HTTPS://Example.com/a-b.\n'),
                         'hello visit https://example.com/a-b.')

    def test_saved_artifacts_unchanged(self):
        expected = {
            'phishing_svm_model.pkl': '8979f3d0d49ed00d20f46bb90f8306bbbaa0b3a6a741f9c286614fb42abe1d48',
            'tfidf_vectorizer.pkl': '97e833d367d8f6289de9610896c8aae982e753be5e3a2bf80de67a639e95fb79',
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((BASE_DIR / name).read_bytes()).hexdigest(), digest)

    def test_prediction_matches_saved_pipeline_without_fitting(self):
        for email in ['Dear winner, claim your prize now by sending your bank account details.',
                      'Hi team, please find the meeting agenda for tomorrow. We will discuss the project schedule. Thanks, John.']:
            expected = int(model.predict(tfidf.transform([clean_text(email)]))[0])
            with patch.object(tfidf, 'fit', side_effect=AssertionError('Must not fit')), \
                 patch.object(tfidf, 'fit_transform', side_effect=AssertionError('Must not fit')), \
                 patch.object(model, 'fit', side_effect=AssertionError('Must not fit')):
                response = self.client.post('/predict', json={'email': email})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['prediction'], expected)
            self.assertEqual(response.json['label'], 'phishing/scam' if expected else 'legitimate')

    def test_invalid_inputs(self):
        for payload in [{}, {'email': None}, {'email': 123}, {'email': ''},
                        {'email': '<b>!!!</b>'}, {'email': 'x' * 50001}, []]:
            with self.subTest(payload_type=type(payload).__name__):
                response = self.client.post('/predict', json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json)
        self.assertEqual(self.client.post('/predict', data='{', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/predict', data='text').status_code, 415)
        self.assertEqual(self.client.post('/predict', data='x' * 300000, content_type='application/json').status_code, 413)

    def test_page_and_assets(self):
        for path in ['/', '/static/style.css', '/static/script.js']:
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)

    def test_attribution_preserves_features_and_reconstructs_score(self):
        for email in ['Hi this is samuel can you wire me $3000', 'Dear winner claim your prize', 'zzzxqvzzz']:
            features = tfidf.transform([clean_text(email)])
            original = features.copy()
            prediction = model.predict(features).tolist()
            explanation = explain_features(features, limit=20000)
            signals = explanation['phishing'] + explanation['legitimate']
            score = sum(s['contribution'] for s in signals) + float(model.intercept_[0])
            self.assertAlmostEqual(score, float(model.decision_function(features)[0]), places=10)
            self.assertEqual((features != original).nnz, 0)
            self.assertEqual(model.predict(features).tolist(), prediction)

    def test_signal_order_and_limit(self):
        explanation = explain_features(tfidf.transform([clean_text('Hi this is samuel can you wire me $3000')]))
        for direction in ['phishing', 'legitimate']:
            values = [s['contribution'] for s in explanation[direction]]
            self.assertLessEqual(len(values), 3)
            self.assertEqual(values, sorted(values, reverse=direction == 'phishing'))
            self.assertTrue(all(v > 0 if direction == 'phishing' else v < 0 for v in values))

    def test_unknown_vocabulary(self):
        response = self.client.post('/predict', json={'email': 'zzzxqvzzz'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['explanation'], {'phishing': [], 'legitimate': [], 'recognized_features': 0})

    def test_explanation_failure_preserves_prediction(self):
        with patch('app.explain_features', side_effect=RuntimeError('Test failure')), self.assertLogs(app.logger, level='ERROR'):
            response = self.client.post('/predict', json={'email': 'Hi this is samuel can you wire me $3000'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['prediction'], 0)
        self.assertIsNone(response.json['explanation'])

    def test_samuel_explanation(self):
        response = self.client.post('/predict', json={'email': 'Hi this is samuel can you wire me $3000'})
        self.assertEqual(response.json['prediction'], 0)
        self.assertIn('wire', [s['feature'] for s in response.json['explanation']['phishing']])


if __name__ == '__main__':
    unittest.main()
