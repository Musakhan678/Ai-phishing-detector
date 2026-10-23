"""Run with python -m unittest discover -s tests -v."""
import hashlib
import unittest
from types import SimpleNamespace
import numpy as np
from scipy.sparse import csr_matrix
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
            # Reconstruction must include hidden features, not the display subset.
            raw_contributions = features.data * model.coef_[0, features.indices]
            score = float(raw_contributions.sum()) + float(model.intercept_[0])
            self.assertAlmostEqual(score, float(model.decision_function(features)[0]), places=10)
            self.assertEqual((features != original).nnz, 0)
            self.assertEqual(model.predict(features).tolist(), prediction)

    def test_display_filter_keeps_meaningful_phrases_and_threshold_boundary(self):
        names = np.array(['the', 'subject', 'dear', 'this is', 'your account',
                          'account verification', 'tiny', 'boundary', 'negative tiny'])
        coefficients = np.array([[.9, -.8, .7, -.6, .4, -.3, .009, -.01, -.009]])
        features = csr_matrix(np.ones((1, len(names))))
        with patch('app.feature_names', names), \
             patch('app.model', SimpleNamespace(coef_=coefficients)):
            explanation = explain_features(features)
        self.assertEqual(explanation['phishing'],
                         [{'feature': 'your account', 'contribution': .4}])
        self.assertEqual(explanation['legitimate'], [
            {'feature': 'account verification', 'contribution': -.3},
            {'feature': 'boundary', 'contribution': -.01}])
        self.assertEqual(explanation['recognized_features'], len(names))

    def test_filter_can_leave_both_directions_empty(self):
        with patch('app.feature_names', np.array(['the', 'dear'])), \
             patch('app.model', SimpleNamespace(coef_=np.array([[.5, -.5]]))):
            explanation = explain_features(csr_matrix([[1., 1.]]))
        self.assertEqual(explanation, {'phishing': [], 'legitimate': [],
                                      'recognized_features': 2})

    def test_prediction_regression_before_and_after_display_filtering(self):
        emails = ['Hi this is samuel can you wire me $3000',
                  'Dear winner, claim your prize now by sending your bank account details.',
                  'The subject is dear and this is the email', 'zzzxqvzzz']
        for email in emails:
            with self.subTest(email=email):
                features = tfidf.transform([clean_text(email)])
                original = features.copy()
                before_prediction = model.predict(features).copy()
                before_score = model.decision_function(features).copy()
                # Empty filler list and zero cutoff reproduce the old display policy.
                with patch('app.EXPLANATION_FILLER_WORDS', frozenset()), \
                     patch('app.MIN_EXPLANATION_CONTRIBUTION', 0):
                    before = self.client.post('/predict', json={'email': email})
                after = self.client.post('/predict', json={'email': email})
                self.assertEqual(before.status_code, 200)
                self.assertEqual(after.status_code, 200)
                self.assertEqual(before.json['prediction'], after.json['prediction'])
                self.assertEqual(after.json['prediction'], int(before_prediction[0]))
                explain_features(features)
                np.testing.assert_array_equal(model.predict(features), before_prediction)
                np.testing.assert_array_equal(model.decision_function(features), before_score)
                np.testing.assert_array_equal(features.data, original.data)
                np.testing.assert_array_equal(features.indices, original.indices)
                np.testing.assert_array_equal(features.indptr, original.indptr)

    def test_explanation_copy(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('Words pushing the model toward phishing/scam', html)
        self.assertIn('Words pushing the model toward legitimate', html)
        self.assertIn('statistical associations learned from training data', html)

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
