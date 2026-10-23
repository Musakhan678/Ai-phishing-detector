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
