"""Web interface for the existing fitted phishing detector."""
from pathlib import Path
import re
import joblib
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

BASE_DIR = Path(__file__).resolve().parent
model = joblib.load(BASE_DIR / 'phishing_svm_model.pkl')
tfidf = joblib.load(BASE_DIR / 'tfidf_vectorizer.pkl')
if model.classes_.tolist() != [0, 1]:
    raise ValueError('Explanations require class order [0, 1].')
feature_names = tfidf.get_feature_names_out()
# Display policy only: never remove these words from the inference input.
EXPLANATION_FILLER_WORDS = frozenset('''
    the a an and or to of is are was were be been being am do does did
    have has had this that these those it its i me my we us our you your
    he him his she her they them their in on at by for from with as if
    but so than then can could would should will shall may might not
    subject dear hi hello regards sincerely thanks thank please
'''.split())
# SVM score units, not a probability or a classification threshold.
MIN_EXPLANATION_CONTRIBUTION = 0.01
app = Flask(__name__)
app.config['DEBUG'] = False
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024


def clean_text(text):
    """Exactly the preprocessing used during training."""
    text = text.lower()
    text = re.sub(r'<.*?>', ' ', text)
    text = re.sub(r'[^\w\s:/.-]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def explain_features(features, limit=3):
    """Filter the displayed signals only; leave all inference features intact.

    Phrases survive if at least one word is informative, so 'your account'
    is retained while 'this is' is omitted. Hidden signals still affect score.
    """
    signals = []
    for index, value in zip(features.indices, features.data):
        feature = str(feature_names[index])
        contribution = float(value * model.coef_[0, index])
        if (all(word in EXPLANATION_FILLER_WORDS for word in feature.split())
                or abs(contribution) < MIN_EXPLANATION_CONTRIBUTION):
            continue
        signals.append({'feature': feature, 'contribution': contribution})
    return {
        'phishing': sorted((s for s in signals if s['contribution'] > 0),
                           key=lambda s: -s['contribution'])[:limit],
        'legitimate': sorted((s for s in signals if s['contribution'] < 0),
                             key=lambda s: s['contribution'])[:limit],
        'recognized_features': int(features.nnz),
    }


@app.get('/')
def index():
    return render_template('index.html')


@app.post('/predict')
def predict():
    if not request.is_json:
        return jsonify(error='Send the email as JSON.'), 415
    try:
        data = request.get_json()
    except BadRequest:
        return jsonify(error='Invalid JSON request.'), 400
    email = data.get('email') if isinstance(data, dict) else None
    if not isinstance(email, str):
        return jsonify(error='Provide email text.'), 400
    if len(email) > 50000:
        return jsonify(error='Keep the email under 50,000 characters.'), 400
    cleaned_email = clean_text(email)
    if not cleaned_email:
        return jsonify(error='Paste an email containing text before analyzing.'), 400
    try:
        features = tfidf.transform([cleaned_email])
        prediction = int(model.predict(features)[0])
        if prediction not in (0, 1):
            raise ValueError('Unexpected model label')
    except Exception:
        app.logger.exception('Email prediction failed')
        return jsonify(error='Analysis failed. Please try again.'), 500
    # Explanations never change prediction, even if explanation generation fails.
    try:
        explanation = explain_features(features)
    except Exception:
        app.logger.exception('Feature explanation failed')
        explanation = None
    return jsonify(prediction=prediction,
                   label='phishing/scam' if prediction == 1 else 'legitimate',
                   explanation=explanation)


@app.errorhandler(RequestEntityTooLarge)
def too_large(error):
    return jsonify(error='Request too large. Paste a shorter email.'), 413


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
