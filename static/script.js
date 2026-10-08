const form = document.querySelector('#email-form');
const email = document.querySelector('#email');
const analyze = document.querySelector('#analyze');
const clear = document.querySelector('#clear');
const statusMessage = document.querySelector('#status');
const result = document.querySelector('#result');
const title = document.querySelector('#result-title');
const detail = document.querySelector('#result-detail');
function resetResult() {
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
    title.textContent = phishing ? 'Phishing / scam' : 'Legitimate';
    detail.textContent = phishing
      ? 'The model flagged this email. Be cautious with links, attachments, and requests for money or personal information.'
      : 'The model classified this email as legitimate. Still verify the sender and any unusual requests.';
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
