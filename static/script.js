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
const predictionGuide = document.querySelector('#prediction-guide');
const selectedPattern = document.querySelector('#selected-pattern');
const aiExplanation = document.querySelector('#ai-explanation');
function renderWarnings(warnings) {
  const list = document.querySelector('#warning-signs');
  list.replaceChildren();
  document.querySelector('#warning-empty').hidden = warnings.length > 0;
  for (const warning of warnings) {
    const item = document.createElement('li');
    const heading = document.createElement('h5');
    heading.textContent = warning.title;
    const description = document.createElement('p');
    description.textContent = warning.description;
    const evidence = document.createElement('p');
    evidence.className = 'hint';
    evidence.textContent = `Matched wording: “${warning.evidence}”`;
    item.append(heading, description, evidence);
    list.appendChild(item);
  }
}
function renderAdvice(advice, calmResult) {
  document.querySelector('#advice-introduction').textContent = calmResult
    ? 'Nothing suspicious stood out in this email. Here are a few simple precautions to keep in mind:'
    : advice.introduction;
  const list = document.querySelector('.safety-actions');
  list.replaceChildren();
  for (const step of advice.steps) {
    const item = document.createElement('li');
    item.textContent = step;
    list.appendChild(item);
  }
  document.querySelector('#caution-reminder').textContent = advice.reminder;
}
let analyzedEmail = '';

function showPattern(signal) {
  document.querySelector('#selected-pattern-title').textContent = `Learned feature: “${signal.feature}”`;
  const direction = signal.contribution > 0 ? 'phishing/scam' : 'legitimate';
  document.querySelector('#selected-pattern-direction').textContent =
    `This feature pushes toward ${direction} in this email. Its TF-IDF value multiplied by its learned SVM weight gives a ${signal.contribution > 0 ? 'positive' : 'negative'} contribution. This describes the model, not whether the request is safe.`;
  // Match literal feature words with whitespace between them. Do not fabricate
  // raw context when cleaning/tokenization made a phrase non-contiguous.
  const escaped = signal.feature.split(' ').map(word => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const pattern = new RegExp(`(?<![\\p{L}\\p{N}_])${escaped.join('\\s+')}(?![\\p{L}\\p{N}_])`, 'iu');
  const match = pattern.exec(analyzedEmail);
  const context = document.querySelector('#selected-pattern-context');
  if (match) {
    const start = Math.max(0, match.index - 70);
    const end = Math.min(analyzedEmail.length, match.index + match[0].length + 70);
    context.textContent = `${start ? '…' : ''}${analyzedEmail.slice(start, end)}${end < analyzedEmail.length ? '…' : ''}`;
  } else {
    context.textContent = 'No direct matching passage in the original email. This feature was found after text cleaning and tokenization; no context is inferred.';
  }
  selectedPattern.hidden = false;
  predictionGuide.open = true;
  aiExplanation.open = true;
  // Wait for the disclosures to lay out, then move only as far as necessary.
  // Keep focus on the activating button; the existing live region announces
  // the explanation without introducing an unexpected keyboard focus change.
  requestAnimationFrame(() => {
    if (selectedPattern.hidden || result.hidden) return;
    selectedPattern.scrollIntoView({
      behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
      block: 'nearest',
      inline: 'nearest',
    });
  });
}
function renderSignals(id, signals) {
  const list = document.querySelector(id);
  list.replaceChildren();
  for (const signal of signals) {
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'pattern-button';
    button.textContent = signal.feature;
    button.setAttribute('aria-label', `Explain pattern: ${signal.feature}`);
    button.setAttribute('aria-controls', 'selected-pattern');
    button.addEventListener('click', () => showPattern(signal));
    item.appendChild(button);
    list.appendChild(item);
  }
  if (!signals.length) {
    const item = document.createElement('li');
    item.textContent = 'No notable text patterns to display';
    list.appendChild(item);
  }
}
function resetResult() {
  analyzedEmail = '';
  aiExplanation.open = false;
  predictionGuide.open = false;
  selectedPattern.hidden = true;
  document.querySelector('#selected-pattern-context').textContent = '';
  delete document.documentElement.dataset.prediction;
  delete result.dataset.warningException;
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
    const warningException = !phishing && (data.warning_signs || []).length > 0;
    result.dataset.warningException = String(warningException);
    document.documentElement.dataset.prediction = phishing ? 'phishing' : warningException ? 'warning' : 'legitimate';
    title.textContent = phishing ? 'Warning: This email may be a scam.'
      : warningException ? 'The AI found no strong scam pattern, but warning signs were detected.'
        : 'No strong scam warning detected';
    detail.textContent = phishing
      ? 'Our AI found text patterns associated with suspicious emails. This is a warning, not proof that the sender is a scammer.'
      : warningException
        ? 'The separate checks found concerning wording. Read the warning signs below before responding. The AI can miss scams.'
        : 'Our AI did not detect strong signs of a scam in this email. However, AI can make mistakes, so remain cautious.';
    renderWarnings(data.warning_signs || []);
    document.querySelector('#warning-empty').textContent = !phishing && !warningException
      ? "No specific warning signs were found in the email's text. Stay alert for unusual requests."
      : 'No specific warning signs identified from the text alone. Scams can still be present.';
    renderAdvice(data.safety_advice, !phishing && !warningException);
    const explanation = data.explanation;
    analyzedEmail = email.value;
    signalGroups.hidden = !explanation || explanation.recognized_features === 0;
    explanationSummary.textContent = !explanation
      ? 'The prediction is available, but its explanation could not be generated.'
      : explanation.recognized_features === 0
        ? 'No known words or phrases were recognized. The prediction comes from the model’s baseline alone.'
        : 'Actual model phrases are preferred, followed by security-related single words. Within each group, stronger contributions appear first. This is a selected view, not the complete explanation; hidden features still affect the prediction.';
    renderSignals('#phishing-signals', explanation?.phishing || []);
    renderSignals('#legitimate-signals', explanation?.legitimate || []);
    result.className = `result ${phishing ? 'phishing' : 'legitimate'}`;
    result.hidden = false;
    title.focus();
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
