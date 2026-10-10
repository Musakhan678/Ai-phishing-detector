# Email Check — AI Phishing & Scam Detector

A college passion project that turns a trained text classifier into an understandable web application. Paste an email to receive a **legitimate** or **phishing/scam** prediction and see a few words or phrases that influenced the model.

**Evaluation transparency:** the model achieved approximately **99.56% accuracy on its held-out internal test**, but **70% on a small independent 100-email validation set**. These measure performance on different email distributions; the internal result is not a claim of 99.56% accuracy on arbitrary real-world emails.

## Features

- Responsive Flask + HTML/CSS/JavaScript interface with loading, error, and Clear states.
- Existing Linear SVM inference: `0 = legitimate`, `1 = phishing/scam`.
- Feature explanations using learned coefficients and the submitted email's TF-IDF values.
- Muted red lock/background for phishing results, green for legitimate results, and smooth transitions that respect reduced-motion preferences.
- Input validation and warnings that a legitimate prediction does not guarantee safety.
- No retraining, confidence percentages, or threshold adjustments during inference.

## Architecture

```text
Browser: email form
    │ POST /predict, JSON {"email": "..."}
    ▼
Flask: validate → exact clean_text()
    ▼
Saved TfidfVectorizer.transform([cleaned_email])
    ▼
Saved LinearSVC.predict() → original classification
    │
    └── Read-only feature contributions → explanation
    ▼
JSON response → prediction card, signals, and page theme
```

The artifacts load once at startup, using paths relative to `app.py`. The same transformed features are used for prediction and explanation; explanation never changes those features or the decision threshold. If explanation generation fails, the prediction is still returned.

```text
Ai-phishing-detector/
├── app.py                       # Flask routes, cleaning, inference, attribution
├── phishing_svm_model.pkl       # Existing fitted LinearSVC
├── tfidf_vectorizer.pkl         # Existing fitted vectorizer
├── requirements.txt             # Tested dependency versions
├── templates/index.html         # Form, result, and explanation cards
├── static/
│   ├── style.css                # Responsive layout and prediction themes
│   ├── script.js                # Requests, rendering, and UI state
│   └── lock.svg                 # Original standalone lock asset
└── tests/test_app.py             # Application and artifact integrity tests
```

The header uses an inline SVG so its colors can transition with the prediction theme.

## Training methodology

The ML development was completed separately in Google Colab, and the fitted artifacts were exported and successfully loaded in PyCharm. This repository contains the inference application, not a reproducible training pipeline or the original datasets.

The project author reports:

- A cleaned combination of Nazario phishing emails, Nigerian scam emails, and legitimate emails was used for training.
- Near-duplicate/template grouping was used to reduce leakage between training and evaluation splits.
- A fitted `TfidfVectorizer` uses a 20,000-feature vocabulary with unigrams and bigrams.
- A scikit-learn `LinearSVC` produces the binary classification.

Grouping reduces leakage risk; it does not establish that every form of similarity or distribution bias has been eliminated. Hyperparameters, split implementation, and additional training details are not documented here beyond the information provided by the author.

### Exact preprocessing

Incoming text uses the same cleaning function as training:

```python
def clean_text(text):
    text = text.lower()
    text = re.sub(r'<.*?>', ' ', text)
    text = re.sub(r'[^\w\s:/.-]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
```

Inference uses only `transform()` and `predict()`. It never calls `fit()` or `fit_transform()` on submitted emails.

## Evaluation

These results were supplied by the project author from prior ML evaluation. They were **not rerun by the web application tests**, and the evaluation corpora are not included in this repository.

| Evaluation | Dataset size | Reported accuracy | Interpretation |
| --- | ---: | ---: | --- |
| Held-out internal test | 1,583 | ≈99.56% | Strong performance within the internal data distribution |
| Small independent validation | 100: 77 legitimate, 23 phishing | 70% | All 23 phishing emails detected, but 30 legitimate emails falsely flagged |
| Non-overlapping SpamAssassin evaluation | 5,209 | ≈75.54% | 3,481 of 3,491 legitimate emails classified correctly |

### Internal test

Confusion matrix, with rows = actual labels and columns = predicted labels in `[legitimate, phishing/scam]` order:

| Actual / predicted | Legitimate | Phishing/scam |
| --- | ---: | ---: |
| Legitimate | 600 | 2 |
| Phishing/scam | 5 | 976 |

The model correctly classified 1,576 of 1,583 emails. This internal result should not be substituted for external performance.

### Independent 100-email validation

The validation set was deduplicated and had zero exact overlap with the training corpus. Its confusion matrix, derived from the supplied counts, is:

| Actual / predicted | Legitimate | Phishing/scam |
| --- | ---: | ---: |
| Legitimate | 47 | 30 |
| Phishing/scam | 0 | 23 |

The model detected all phishing examples in this small sample, but falsely flagged 30 of 77 legitimate emails, particularly commercial-style messages. This produces **70 correct classifications out of 100**, not 99.56%. A small sample and zero exact overlap do not guarantee broad representativeness or absence of related templates.

### SpamAssassin evaluation

On 5,209 emails reported as non-overlapping with training, overall accuracy was approximately 75.54%. Legitimate classification was strong: 3,481 of 3,491 legitimate emails were correctly classified. Spam and phishing are different categories; this result should be interpreted within the evaluation's labeling protocol, which is not fully documented here. A complete confusion matrix is not reconstructed from rounded accuracy.

## How explanations work

For a binary LinearSVC with class order `[0, 1]`:

```text
feature contribution = email's TF-IDF feature value × learned coefficient
SVM decision score = intercept + sum(all feature contributions)
```

Positive contributions push toward phishing/scam; negative contributions push toward legitimate. The page lists up to three strongest nonzero contributions in each direction, using only features present in the cleaned email. It does not display calibrated probabilities or confidence percentages.

These are **model signals, not proof of phishing or safety**. Unigrams and bigrams may overlap; the displayed subset does not add up to the full decision score. The intercept also affects the result. If no vocabulary features are recognized, the prediction comes from the intercept alone.

### A concrete limitation: a short wire-transfer request

For `Hi this is samuel can you wire me $3000`, the unchanged cleaning produces `hi this is samuel can you wire me 3000`.

The saved model predicts **legitimate**. The word `wire` contributes approximately **+0.1113** toward phishing. Across all recognized features, positive contributions total approximately **+0.2623** and negative contributions **−0.2319**, leaving **+0.0304**. Adding the intercept **−0.3358** gives a decision score of approximately **−0.3054**, on the legitimate side of the original boundary.

This explains the model's arithmetic, not the request's safety. It illustrates how a short, potentially suspicious request can be missed. The model was not modified to force a different result.

## Run locally / in PyCharm

Use **Python 3.12** and a project virtual environment. In PyCharm, select that environment as the project interpreter, then run these commands in its terminal:

```sh
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your local browser. Keep the terminal running; stop with Ctrl+C. After changing static files, refresh with Ctrl+F5.

scikit-learn is pinned to **1.6.1**, matching the version recorded in both saved artifacts. The other declared dependencies use versions tested with these artifacts on Python 3.12. Only load trusted pickle/joblib files: deserializing untrusted artifacts can execute code.

The Flask development server is for local development. This repository does not currently provide a public deployment; GitHub hosts the code, not the running Flask application.

## Testing

```sh
python -m unittest discover -s tests -v
```

Tests cover exact preprocessing, API/direct-pipeline prediction agreement without fitting, invalid inputs, page/assets, unchanged artifact checksums, contribution ordering, reconstruction of the decision score, preservation of features/predictions, unknown vocabulary, and explanation failure handling.

Application tests verify integration and behavior; they do not remeasure dataset-level ML accuracy.

## Known limitations and safety

- Distribution shift can substantially change accuracy and false-positive rates, as the external results demonstrate.
- Short messages and unfamiliar wording can be missed. Words outside the fitted vocabulary contribute no features.
- Text classification does not authenticate the sender, inspect email headers, scan attachments, or verify linked websites.
- No SVM score or feature contribution is a calibrated probability.
- A legitimate label is not a guarantee of safety. Verify unusual requests for money or credentials through an independently trusted channel.
- The application does not intentionally persist email text or log its contents. It sends submitted text to the Flask server for processing; hosting infrastructure would need a separate privacy review before public deployment.
- Requests are limited to 50,000 email characters and 256 KiB total request size. There is no production rate limiting in this local prototype.

## Project status

Local application development and testing. Public hosting and production deployment are separate future steps. The trained model and vectorizer remain unchanged.
