import joblib

model = joblib.load("phishing_svm_model.pkl")
tfidf = joblib.load("tfidf_vectorizer.pkl")

print("Model loaded successfully!")
print("Model type:", type(model))
print("Vectorizer type:", type(tfidf))
print("Vocabulary size:", len(tfidf.vocabulary_))