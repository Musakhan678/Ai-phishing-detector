/* Optional browser regression suite. Requires Node + Playwright + Chromium.
   Start Flask separately, then run:
   BASE_URL=http://127.0.0.1:5014 node tests/frontend-regression.cjs
   CHROMIUM_PATH may override the installed Chromium executable.
   This adds no production dependencies and never mocks or alters the model.
*/
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const base = process.env.BASE_URL || 'http://127.0.0.1:5014';
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base);
    const navigationLock = await page.locator('.brand-lock .lock-body').evaluate(el => getComputedStyle(el).fill);
    for (const href of ['#home', '#how-it-works', '#check-email']) {
      assert.equal(await page.locator(href).count(), 1);
    }
    assert.equal(await page.locator('.hero-art').getAttribute('aria-hidden'), 'true');
    assert.equal(await page.locator('.hero-art img').getAttribute('alt'), '');
    await page.locator('.hero-cta').click();
    assert.equal(new URL(page.url()).hash, '#check-email');
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(base);
    await page.screenshot({ path: '/tmp/email-check-redesign-desktop.png', fullPage: true });
    const examples = JSON.parse(fs.readFileSync(path.join(__dirname, 'example_emails.json'), 'utf8'));
    examples.disagreement = 'Hi this is samuel can you wire me $3000';
    examples.urgent_disagreement = 'Hi, I need you to transfer $3,000 urgently. Please send the money today.';
    examples.quick_favor_disagreement = 'Subject: Quick Favor\n\nHi,\n\nI need you to transfer $3,000 urgently. Please send the money today.\n\nThanks';
    for (const [name, email] of Object.entries(examples)) {
      const response = await page.request.post(`${base}/predict`, { data: { email } });
      assert.equal(response.status(), 200);
      const data = await response.json();
      const disagreement = name.includes('disagreement');
      if (disagreement) {
        // Explicitly establish the real ML/text-check disagreement; do not assume it.
        assert.equal(data.prediction, 0);
        assert.ok(data.warning_signs.length > 0);
        assert.equal(data.safety_advice.mode, 'warning_exception');
      }
      await page.locator('#email').fill(email);
      await page.locator('#analyze').click();
      await page.locator('#result:not([hidden])').waitFor();
      const calmResult = data.prediction === 0 && data.warning_signs.length === 0;
      assert.equal(await page.locator('#advice-introduction').textContent(), calmResult
        ? 'Nothing suspicious stood out in this email. Here are a few simple precautions to keep in mind:'
        : data.safety_advice.introduction);
      assert.deepEqual(await page.locator('.safety-actions li').allTextContents(), data.safety_advice.steps);
      assert.equal(await page.locator('#caution-reminder').textContent(), data.safety_advice.reminder);
      assert.equal(await page.locator('#ai-explanation').evaluate(el => el.open), false);
      assert.equal(await page.locator('#warning-signs li').count(), data.warning_signs.length);
      const state = data.prediction === 1 ? 'red' : calmResult ? 'green' : 'yellow';
      assert.equal(await page.locator(`.indicator-${state}`).isVisible(), true);
      assert.equal(await page.locator('.result-indicator svg:visible').count(), 1);
      assert.equal(await page.locator('.brand-lock .lock-body').evaluate(el => getComputedStyle(el).fill), navigationLock);
      const colors = await page.locator('#result').evaluate(el => ({
        background: getComputedStyle(el).backgroundColor,
        topBorder: getComputedStyle(el).borderTopColor,
        heading: getComputedStyle(document.querySelector('#result-title')).color,
      }));
      if (state === 'red') {
        assert.equal(colors.background, 'rgb(255, 240, 241)');
        assert.equal(colors.topBorder, 'rgb(193, 59, 80)');
        assert.equal(colors.heading, 'rgb(144, 33, 56)');
        assert.equal(await page.locator('#result-title').textContent(), 'Warning: This email may be a scam.');
      } else if (state === 'yellow') {
        assert.equal(colors.background, 'rgb(255, 251, 232)');
        assert.equal(colors.topBorder, 'rgb(214, 163, 33)');
        assert.equal(colors.heading, 'rgb(121, 83, 0)');
      } else {
        assert.equal(colors.background, 'rgb(241, 249, 244)');
        assert.equal(await page.locator('#result-title').textContent(), 'No strong scam warning detected');
        assert.equal(await page.locator('#result-detail').textContent(), 'Our AI did not detect strong signs of a scam in this email. However, AI can make mistakes, so remain cautious.');
        assert.equal(await page.locator('#warning-empty').textContent(), "No specific warning signs were found in the email's text. Stay alert for unusual requests.");
      }
      const technicalCopy = page.getByText('These are separate text-matching checks, not the AI prediction. We have not checked the sender, links, or websites.', { exact: true });
      assert.equal(await technicalCopy.count(), 1);
      assert.equal(await technicalCopy.isVisible(), false);
      assert.equal(await technicalCopy.evaluate(el => Boolean(el.closest('#prediction-guide'))), true);
      for (const warning of data.warning_signs) {
        const evidence = page.getByText(`Matched wording: “${warning.evidence}”`, { exact: true });
        assert.equal(await evidence.isVisible(), true);
        assert.equal(await evidence.evaluate(el => Boolean(el.closest('details'))), false);
      }
      if (disagreement) {
        assert.equal(await page.locator('#result-title').textContent(), 'The AI found no strong scam pattern, but warning signs were detected.');
        assert.equal(await page.locator('#result-title').evaluate(el => Boolean(el.closest('details'))), false);
        assert.equal(await page.locator('#result').getAttribute('data-warning-exception'), 'true');
        assert.ok(!(await page.locator('#advice-introduction').textContent()).includes('reassuring'));
        assert.ok(data.safety_advice.steps[0].includes("Don't send money"));
      }
      for (const width of [320, 390, 768, 1440]) {
        await page.setViewportSize({ width, height: 1000 });
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${name}: overflow at ${width}`);
      }
      if (name === 'urgent_disagreement') {
        await page.setViewportSize({ width: 1000, height: 1000 });
        await page.locator('#result').screenshot({ path: '/tmp/email-check-redesign-disagreement.png' });
      }
      await page.locator('#ai-explanation > summary').focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('#ai-explanation').evaluate(el => el.open), true);
      if (await page.locator('.pattern-button').count()) {
        await page.locator('.pattern-button').first().click();
        assert.equal(await page.locator('#selected-pattern').isVisible(), true);
        assert.equal(await page.locator('#prediction-guide').evaluate(el => el.open), true);
      }
      await page.locator('#clear').click();
      assert.equal(await page.locator('#result').isVisible(), false);
      assert.equal(await page.locator('#email').inputValue(), '');
      assert.equal(await page.locator('.result-indicator').isVisible(), false);
      console.log(`PASS ${name}: labels, warnings, exact advice, disclosures, context, mobile layout`);
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(base);
    await page.screenshot({ path: '/tmp/email-check-redesign-mobile.png', fullPage: true });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'auto');
    // Keep a request pending long enough to inspect the existing loading state.
    let release;
    await page.route('**/predict', async route => {
      await new Promise(resolve => { release = resolve; });
      await route.continue();
    });
    await page.locator('#email').fill('Please check this email.');
    await page.locator('#analyze').click();
    await page.waitForFunction(() => document.querySelector('#email-form').getAttribute('aria-busy') === 'true');
    assert.equal(await page.locator('#analyze').isDisabled(), true);
    assert.equal(await page.locator('#status').textContent(), 'Analyzing your email…');
    assert.equal(await page.locator('#result').isVisible(), false);
    await page.waitForFunction(() => document.querySelector('#email').disabled);
    while (!release) await new Promise(resolve => setTimeout(resolve, 10));
    release();
    await page.locator('#result:not([hidden])').waitFor();
    await page.unroute('**/predict');
    // Loading state and failed requests must not leave a previous warning visible.
    await page.route('**/predict', route => route.abort());
    await page.locator('#email').fill('Please check this email.');
    await page.locator('#analyze').click();
    await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Cannot reach'));
    assert.equal(await page.locator('#result').isVisible(), false);
    assert.equal(await page.locator('#analyze').isEnabled(), true);
    assert.deepEqual(errors, []);
    console.log('PASS mandatory disagreement regression, navigation, reduced motion, error state, no JS errors');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
