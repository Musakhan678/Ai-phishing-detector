const form = document.querySelector('#email-form');
const email = document.querySelector('#email');
const analyze = document.querySelector('#analyze');
const clear = document.querySelector('#clear');
const statusMessage = document.querySelector('#status');
const result = document.querySelector('#result');
const title = document.querySelector('#result-title');
const detail = document.querySelector('#result-detail');
const explanationSummary = document.querySelector('#explanation-summary');
const signalGroups = document.querySelector('#signal-groups');
function renderSignals(id, signals) {
  const list = document.querySelector(id);
  list.replaceChildren();
  for (const signal of signals) {
    const item = document.createElement('li');
    item.textContent = signal.feature;
    list.appendChild(item);
  }
  if (!signals.length) {
    const item = document.createElement('li');
    item.textContent = 'No notable text features to display';
    list.appendChild(item);
  }
}
function resetResult() {
  delete document.documentElement.dataset.prediction;
  result.hidden = true;
  statusMessage.textContent = '';
  statusMessage.className = '';
}
email.addEventListener('input', resetResult);
clear.addEventListener('click', () => {
  form.reset();
  resetResult();
  email.focus();
});
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  resetResult();
  if (!email.value.trim()) {
    statusMessage.textContent = 'Paste an email before analyzing.';
    statusMessage.className = 'error';
    email.focus();
    return;
  }
  analyze.disabled = clear.disabled = email.disabled = true;
  form.setAttribute('aria-busy', 'true');
  statusMessage.textContent = 'Analyzing your email…';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(form.action, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value }), signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Analysis failed. Please try again.');
    if (data.prediction !== 0 && data.prediction !== 1) throw new Error('Unexpected response. Please try again.');
    const phishing = data.prediction === 1;
    document.documentElement.dataset.prediction = phishing ? 'phishing' : 'legitimate';
    title.textContent = phishing ? 'Phishing / scam' : 'Legitimate';
    detail.textContent = phishing
      ? 'The model flagged this email. Be cautious with links, attachments, and requests for money or personal information.'
      : 'The model classified this email as legitimate. Still verify the sender and any unusual requests.';
    const explanation = data.explanation;
    signalGroups.hidden = !explanation || explanation.recognized_features === 0;
    explanationSummary.textContent = !explanation
      ? 'The prediction is available, but its explanation could not be generated.'
      : explanation.recognized_features === 0
        ? 'No known words or phrases were recognized. The prediction comes from the model’s baseline alone.'
        : 'The strongest remaining words and phrases are shown first in each direction. Common filler words and very small contributions are hidden from this display only; they still affect the model’s prediction.';
    renderSignals('#phishing-signals', explanation?.phishing || []);
    renderSignals('#legitimate-signals', explanation?.legitimate || []);
    result.className = `result ${phishing ? 'phishing' : 'legitimate'}`;
    result.hidden = false;
    statusMessage.textContent = 'Analysis complete.';
  } catch (error) {
    statusMessage.className = 'error';
    statusMessage.textContent = error.name === 'AbortError'
      ? 'The request timed out. Please try again.'
      : error instanceof TypeError
        ? 'Cannot reach the server. Check your connection and try again.'
        : error.message;
  } finally {
    clearTimeout(timeout);
    analyze.disabled = clear.disabled = email.disabled = false;
    form.removeAttribute('aria-busy');
  }
});
