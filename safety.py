"""Conservative text checks for advice, independent of the ML pipeline.

Rules report literal wording, not intent or authenticity. They can miss indirect
requests and can flag quoted examples. No sender, link, or reputation checks.
"""
import re

REQUEST = re.compile(r'\b(?:provide|confirm|enter|send|share|submit|reply with|give us)\b', re.I)
NEGATION = re.compile(r"\b(?:never|do not|don't|no need to|must not|should not)\b", re.I)


def _requested(text, target):
    for action in REQUEST.finditer(text):
        # Avoid interpreting common safety advice as a request for secrets.
        prefix = text[max(0, action.start() - 35):action.start()]
        if NEGATION.search(prefix):
            continue
        match = re.match(r'[^.!?\n]{0,80}?\b(' + target + r')\b', text[action.end():], re.I)
        if match:
            return text[action.start():action.end() + match.end()]
    return None


def detect_warning_signs(text):
    """Return at most four matched wording checks; never classify the email."""
    warnings = []

    def add(code, title, description, evidence):
        if evidence:
            warnings.append(dict(code=code, title=title, description=description,
                                 evidence=evidence))

    secrets = _requested(text, r'passwords?|verification codes?|one[ -]time (?:codes?|passwords?)|passcodes?|otps?')
    add('secrets', 'A request for a password or code',
        'The text asks for a password or verification code. Do not share these in response to an unexpected email.', secrets)
    financial = _requested(text, r'bank details|bank account details|payment details|financial details|credit card (?:details|number)|account number')
    if not financial:
        for match in re.finditer(r'\b(?:wire|transfer|send)\b[^.!?\n]{0,45}?(?:\$\s*\d[\d,]*|\b(?:money|funds|payment|bank details)\b)', text, re.I):
            if not NEGATION.search(text[max(0, match.start() - 35):match.start()]):
                financial = match.group()
                break
    add('money', 'A request for money or financial details',
        'The text asks for money or financial details. Check the request through a trusted official channel before acting.', financial)
    suspension = re.search(r'\baccount\b[^.!?\n]{0,50}\b(?:suspended|restricted|blocked|disabled|closed)\b', text, re.I)
    add('account', 'A claim that an account is restricted',
        'The text claims an account is restricted or suspended. This tool has not verified that claim.', suspension.group() if suspension else None)
    pressure = re.search(r'\b(?:act now|respond immediately|urgent action required|take immediate action)\b', text, re.I)
    # A deadline alone (e.g. homework) is not enough; require another risk check.
    if not pressure and warnings:
        pressure = re.search(r'\b(?:urgent|urgently|immediately|before the deadline|within \d+ hours?)\b', text, re.I)
    add('pressure', 'Pressure to act quickly',
        'The wording pressures you to act quickly. Pause and check the request before responding.', pressure.group() if pressure else None)
    return warnings


def build_safety_advice(prediction, warnings):
    """Choose wording only. Never override the model's label or score."""
    if prediction == 0 and not warnings:
        return {
            'mode': 'calm',
            'introduction': "No strong signs of a scam were detected in the email's text. This is reassuring, but the email hasn't been verified as safe.",
            'steps': [
                'You can review the email as usual, but be cautious about unexpected requests.',
                "If you're asked for money, passwords, or personal details, verify the sender first.",
                'If something seems unusual, contact the sender through a trusted channel.',
            ],
            'reminder': 'The AI can miss scams. Stay cautious if anything seems unusual.',
        }
    steps = [
        "Don't click unexpected links or open unfamiliar attachments.",
        "Don't share passwords, verification codes, or financial details.",
        'Contact the organization through its official website or a trusted phone number.',
    ]
    if prediction == 0:
        codes = {warning['code'] for warning in warnings}
        targeted = []
        if 'secrets' in codes:
            targeted.append("Don't send the password or verification code requested.")
        if 'money' in codes:
            targeted.append("Don't send money or financial details until you have checked the request through a trusted channel.")
        if 'account' in codes:
            targeted.append('Check the account restriction claim through an official website or a phone number you already trust.')
        if 'pressure' in codes:
            targeted.append('Pause before acting. Do not let urgent wording rush you.')
        # Exactly three steps. Multiple matched concerns share the first step.
        steps[0] = ' '.join(targeted) or 'Pause and check the warning signs before responding.'
        return {
            'mode': 'warning_exception',
            'introduction': 'The AI did not flag this email as a scam, but the separate text checks found a warning sign. Follow the cautious steps below; the email has not been verified as safe.',
            'steps': steps,
            'reminder': 'The text checks and AI can disagree. Take the specific warning seriously even when the AI does not flag a scam.',
        }
    return {
        'mode': 'caution',
        'introduction': 'The email contains text patterns associated with scams. Treat unexpected requests cautiously; this is a warning, not proof of fraud.',
        'steps': steps,
        'reminder': 'Check unexpected requests before responding. We have not verified the sender or any links.',
    }
