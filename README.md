# Email Check

A small Flask web application for an existing phishing/scam email classifier.
The saved LinearSVC and TfidfVectorizer are used for inference only, without retraining.
Labels: 0 = legitimate, 1 = phishing/scam. No probability or confidence percentage is displayed.

## Run in PyCharm (Python 3.12)

1. Open this project folder in PyCharm. Choose a Python 3.12 virtual environment as the project interpreter (Settings → Project → Python Interpreter).
2. In the PyCharm terminal, using that interpreter, run:

   ```sh
   python -m pip install -r requirements.txt
   python app.py
   ```

3. Open `http://127.0.0.1:5000` in your local browser. Paste an email and select **Analyze Email**.
4. Stop the server with Ctrl+C. You can also right-click `app.py` and choose **Run** after installing dependencies.

scikit-learn is pinned to 1.6.1, the version recorded in both saved artifacts.
Other numerical dependencies are pinned to the versions verified with these artifacts on Python 3.12.
The Flask development server is for local development; public deployment is a separate step.

## Important files

- `app.py`: loads both artifacts once using paths relative to this file; serves `GET /` and accepts JSON at `POST /predict`.
- `templates/index.html`: email form and result area.
- `static/style.css`: responsive styles, including mobile layout.
- `static/script.js`: submits `{ "email": "..." }` with `fetch`, displays the JSON result, and handles loading, errors, and clearing.
- `requirements.txt`: compatible dependencies.
- `tests/test_app.py`: preprocessing, inference parity, validation, artifact integrity, and asset checks.

The inference sequence is raw text → exact training `clean_text()` → existing `tfidf.transform([cleaned_email])` → existing `model.predict()`.
Never call `fit()` or `fit_transform()` on submitted text. Do not change the artifacts or preprocessing without explicitly planning a separate ML change.

The API accepts up to 50,000 characters and returns a JSON error for invalid input.
It does not store submitted emails or log their contents. Results are displayed as text, not injected HTML.

## Checks

```sh
python -m unittest discover -s tests -v
```

Both artifacts loaded without scikit-learn version mismatch warnings in the tested environment.
Browser checks exercised scam and legitimate result rendering, Clear, invalid-text and network errors, and layout overflow at 390px and 1280px widths.
Sample predictions check integration; they do not establish model accuracy.

## Model limitations

Reported internal evaluation: approximately 99.56% accuracy on 1,583 emails, confusion matrix `[[600, 2], [5, 976]]`.
Reported independent 100-email evaluation: 70% accuracy, detecting all 23 phishing emails but flagging 30 of 77 legitimate emails.
Reported non-overlapping SpamAssassin evaluation: approximately 75.54% accuracy, with 3,481 of 3,491 legitimate emails correctly classified.
These evaluations were supplied by the project author, not rerun by this application.
Predictions can be wrong, particularly for unfamiliar email styles. A legitimate label does not guarantee safety.
