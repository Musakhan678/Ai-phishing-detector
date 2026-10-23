# Email Check — AI Phishing & Scam Detector

A college passion project that turns a trained text classifier into an understandable web application. Paste an email to receive a **legitimate** or **phishing/scam** prediction and see a few words or phrases that influenced the model.

**Evaluation transparency:** there is no single universal accuracy figure. SVM v2a achieved **99.43% on the original internal test**, **88% on a small external set used during development**, and **64.75% on the independent PhishNChips benchmark**. SVM v1 achieved **99.56%**, **70%**, and **60.15%** on those respective evaluations. The development set is not an untouched final benchmark. On PhishNChips, v2a's high phishing precision (**98.05%**) coexists with low recall (**30.1%**), so most phishing-labeled examples were missed.

## Features

- Responsive Flask + HTML/CSS/JavaScript interface with loading, error, and Clear states.
- Existing Linear SVM inference: `0 = legitimate`, `1 = phishing/scam`.
- Feature explanations using learned coefficients and the submitted email's TF-IDF values.
- A neutral page background in every state; muted red lock/result card for phishing, green for legitimate, and a neutral lock before analysis, while analyzing, and after Clear. Lock transitions respect reduced-motion preferences.
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

The following verified results were supplied by the project author. They are additional evaluations and model-version comparisons, not replacements for the earlier results. The web application tests did **not** rerun these dataset evaluations; evaluation corpora and training scripts are not included here.

**Artifact version:** the repository loads the two existing saved artifacts. Their filenames and scikit-learn serialization version do not establish whether they correspond to SVM v1 or v2a. Confirm that provenance before attributing either version's benchmark results to the running website. No artifact was replaced during web development or deployment preparation.

| Evaluation | Composition | SVM v1 accuracy | SVM v2a accuracy | Role |
| --- | --- | ---: | ---: | --- |
| Original internal test | 1,583: 602 legitimate, 981 phishing/scam | 99.56% | 99.43% | Internal held-out evaluation |
| External phishing validation | 100 unique: 77 legitimate, 23 phishing | 70% | **88%** | Small, template-like development evaluation |
| SpamAssassin | 5,209: 3,491 legitimate, 1,718 generic spam | 75.54% | 75.89% | External spam evaluation, not phishing accuracy |
| Independent PhishNChips | 2,000: 1,000 legitimate, 1,000 phishing-labeled | 60.15% | **64.75%** | Independent URL-grounded benchmark |
| Constructed website diagnostics | Six manually constructed examples | 3/6 matched expectations | 5/6 matched expectations | Functional diagnostics, not an accuracy estimate |

All confusion matrices below use **rows = actual labels, columns = predicted labels**, ordered `[legitimate, phishing/scam]`. For SpamAssassin, the second actual category is **generic spam**, not phishing.

### Original internal test

| Version | Confusion matrix | Correct / total | Accuracy |
| --- | --- | ---: | ---: |
| SVM v1 | `[[600, 2], [5, 976]]` | 1,576 / 1,583 | 99.56% |
| SVM v2a | `[[599, 3], [6, 975]]` | 1,574 / 1,583 | 99.43% |

Near-duplicate/template grouping was used to reduce train/test leakage. These results describe the internal distribution, not performance on arbitrary real-world messages. V2a's internal accuracy is slightly lower than v1's; neither internal number should be used as the sole headline for deployment.

### External phishing validation — used during development

| Version | Confusion matrix | Correct / total | Accuracy |
| --- | --- | ---: | ---: |
| SVM v1 | `[[47, 30], [0, 23]]` | 70 / 100 | 70% |
| SVM v2a | `[[67, 10], [2, 21]]` | 88 / 100 | 88% |

The 100 unique emails contain 77 legitimate and 23 phishing messages. Earlier overlap checks reported zero exact overlap with the training corpus. This small, template-like set was used during model development, so it is **not a fully untouched final benchmark**, even without exact duplicates.

V1 detected all 23 phishing examples but falsely flagged 30 legitimate examples, particularly commercial-style messages. V2a reduced those false positives to 10 while missing two phishing examples. The improvement on this development set must not be described as an independent final estimate of generalization.

### SpamAssassin — generic spam is not phishing

| Version | Confusion matrix | Correct / total | Accuracy |
| --- | --- | ---: | ---: |
| SVM v1 | `[[3481, 10], [1264, 454]]` | 3,935 / 5,209 | 75.54% |
| SVM v2a | `[[3481, 10], [1246, 472]]` | 3,953 / 5,209 | 75.89% |

This external evaluation contains 3,491 legitimate emails and 1,718 generic spam emails, previously reported as non-overlapping with training. Both versions correctly classified 3,481 legitimate emails. Many generic spam examples were assigned the legitimate label. **These figures are not phishing detection accuracy:** the positive evaluation category differs from the classifier's intended phishing/scam task.

### Independent PhishNChips benchmark

| Version | Confusion matrix | Correct / total | Accuracy |
| --- | --- | ---: | ---: |
| SVM v1 | `[[983, 17], [780, 220]]` | 1,203 / 2,000 | 60.15% |
| SVM v2a | `[[994, 6], [699, 301]]` | 1,295 / 2,000 | 64.75% |

The benchmark contains 1,000 legitimate and 1,000 phishing-labeled examples. The author reports no exact duplicate cleaned messages and no exact overlaps with v2a training data. Exact-overlap checks do not rule out all semantic or template similarity.

V2a phishing-class metrics:

| Metric | Value | Meaning on these examples |
| --- | ---: | --- |
| Precision | 98.05% | 301 of 307 phishing predictions were correct |
| Recall | 30.1% | 301 of 1,000 phishing-labeled examples were detected |
| F1 | 46.06% | Harmonic mean of precision and recall |

Despite high precision and only six legitimate false positives, **699 of 1,000 phishing-labeled examples were missed**. High precision therefore does not establish reliable phishing coverage.

PhishNChips is a URL-grounded benchmark with many ordinary-looking messages. This application classifies email text; it does not independently verify URL reputation or inspect destinations. That task mismatch helps contextualize the limitations but does not remove the missed detections. The **64.75% independent benchmark result is distinct from the 88% development-set result**.

### Manual website diagnostics

Six constructed diagnostic examples produced 3/6 expected labels for v1 and 5/6 for v2a. These checks help investigate application behavior; six selected examples are not a representative sample and must not be advertised as accuracy estimates. They are also separate from the automated application test suite.

## How explanations work

For a binary LinearSVC with class order `[0, 1]`:

```text
feature contribution = email's TF-IDF feature value × learned coefficient
SVM decision score = intercept + sum(all feature contributions)
```

Positive contributions push toward phishing/scam; negative contributions push toward legitimate. The page lists up to three strongest remaining contributions in each direction, using only features present in the cleaned email. For display only, it hides common filler words, phrases made entirely of filler words, and contributions with absolute magnitude below **0.01 SVM score units**. Phrases such as `your account` survive because they contain an informative word. This cutoff is a presentation choice, not a probability or classification threshold. All original features still contribute to the unchanged prediction and score. If a direction has no qualifying signals, the page says “No notable text features to display.” It does not display calibrated probabilities or confidence percentages.

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

The Flask development server is for local development. Render must use Gunicorn, not `python app.py`. Gunicorn is installed only on non-Windows platforms; PyCharm on Windows can continue using Flask locally. The application has debug disabled. GitHub hosts the code, not the running Flask application.

## Testing

```sh
python -m unittest discover -s tests -v
```

Tests cover exact preprocessing, API/direct-pipeline prediction agreement without fitting, invalid inputs, page/assets, unchanged artifact checksums, contribution ordering, reconstruction of the decision score, preservation of features/predictions, unknown vocabulary, and explanation failure handling.

Application tests verify integration and behavior; they do not remeasure dataset-level ML accuracy.

## Known limitations and safety

- Distribution shift can substantially change accuracy and false-positive rates. The 100-email set was used during development; PhishNChips is the independent benchmark. Neither supplies a universal accuracy figure.
- High precision can coexist with low recall: v2a missed 699 of 1,000 PhishNChips phishing-labeled examples. Text-only inference does not independently establish URL reputation.
- Short messages and unfamiliar wording can be missed. Words outside the fitted vocabulary contribute no features.
- Text classification does not authenticate the sender, inspect email headers, scan attachments, or verify linked websites.
- No SVM score or feature contribution is a calibrated probability.
- A legitimate label is not a guarantee of safety. Verify unusual requests for money or credentials through an independently trusted channel.
- The application does not intentionally persist email text or log its contents. It sends submitted text to the Flask server for processing; hosting infrastructure would need a separate privacy review before public deployment.
- Requests are limited to 50,000 email characters and 256 KiB total request size. There is no production rate limiting in this local prototype.

## Project status

Prepared for Render deployment; no live deployment or public URL has been created. The trained model and vectorizer remain unchanged.


## Publish to GitHub when ready

No deployment credentials or API keys are required in the project. Do not upload `.venv`, `.env`, raw datasets, backups, or private emails. Both existing `.pkl` files must remain in the repository root alongside `app.py`.

### Git workflow (recommended)

In your project terminal, after reviewing your files:

```sh
git status
git add app.py requirements.txt .gitignore .python-version render.yaml README.md tests/test_app.py templates/index.html static/script.js static/style.css
git diff --cached --stat
git commit -m "Prepare Flask app for Render deployment"
git push origin HEAD:main
```

Use these commands only in a clone of this repository with its GitHub origin configured. Review staged changes before committing; never force-push to resolve a rejected update. If another change has reached GitHub, fetch and reconcile it first. The two model files are already tracked in this repository and need no replacement. For a new repository, explicitly add the two trusted artifacts as well.

### If you use downloaded ZIP copies instead of Git

1. Back up your current PyCharm project.
2. On GitHub, open the repository and choose **Add file → Upload files**.
3. Upload the prepared files in their correct locations. For nested files, open `templates/`, `static/`, or `tests/` on GitHub first and upload the corresponding files there. Do not flatten these folders.
4. Include `.gitignore`, `.python-version`, `render.yaml`, `requirements.txt`, `README.md`, and `app.py` in the repository root. Hidden files may need to be made visible in your file explorer.
5. Commit the changes to `main`. Keep the existing model artifacts unchanged.

## Deploy on Render (manual Web Service)

These are instructions for a later user-initiated deployment; preparing these files does not publish the website.

1. Create/sign in to a Render account and connect GitHub through Render's normal authorization screen. Never paste credentials into source files or this chat.
2. Choose **New → Web Service**, select this repository, and choose branch **main**.
3. Choose the **Python** runtime. Leave **Root Directory** blank because `app.py` is at the repository root.
4. Use this build command:

   ```sh
   python -m pip install -r requirements.txt && python -m unittest discover -s tests -v
   ```

5. Use this start command:

   ```sh
   gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 --access-logfile - --error-logfile - app:app
   ```

   `app:app` means the Flask variable `app` in `app.py`. Render supplies `PORT`. One worker keeps the memory footprint modest; two threads allow concurrent requests without changing the model.

6. Set environment variables `PYTHON_VERSION=3.12.14`, `FLASK_DEBUG=0`, `OMP_NUM_THREADS=1`, and `OPENBLAS_NUM_THREADS=1`. The thread limits control CPU use, not model logic. Set the health-check path to `/`.
7. Select the **Free** instance type if Render offers it for your account. Do not select a paid instance or attach a paid database. If Free is unavailable, stop and reassess hosting rather than accepting a charge. No database, disk, API key, or external inference service is needed.
8. For controlled releases, disable automatic deploys until you want GitHub pushes to update the public site. Click **Create Web Service** only when ready to publish.
9. Wait for the build/tests and Gunicorn startup to succeed. Render then provides an HTTPS `onrender.com` address. Use that exact address; do not share `127.0.0.1` or a guessed URL.
10. Test the public page on a phone and computer: submit ordinary and suspicious examples, inspect the result/explanation, press Clear, and test empty input. Share the public address only after verifying it.

Alternatively, `render.yaml` supplies the same configuration for **New → Blueprint**. Review the proposed resources before applying it; it requests a free web service. The manual approach above makes each setting visible. No service has been created by preparing that file.

### Deployment checks and troubleshooting

- Python is pinned in `.python-version` and the Render configuration; scikit-learn 1.6.1 matches both artifacts' saved version. Do not upgrade scikit-learn to fix a loading error without investigating compatibility.
- Missing model file: verify both `.pkl` files are committed in the root, with exact filenames and case. Gitignore intentionally does not exclude these artifacts.
- Module import error: check that Root Directory is blank and start command ends in `app:app`.
- Port errors: use `0.0.0.0:$PORT`; the local Flask address is not a production binding.
- Debug is explicitly disabled; do not enable Flask debug or Gunicorn reload on the public service.
- Free services may sleep while idle and take time to wake. A first prediction may need retrying if startup exceeds the frontend's 30-second request timeout. Check current Render free-tier availability and limits before publishing.
- The application has input-size limits but no authentication or per-client rate limiting. It is a small demonstration, not a production email-security gateway. Do not submit sensitive emails; public hosting also adds network and infrastructure privacy considerations.
- Run application tests before release. Prior dataset accuracy numbers are not a substitute for endpoint and browser checks, and application tests do not validate those dataset metrics.
