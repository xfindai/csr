
import re
import string

from pathlib import Path
from hashlib import sha256

PREFIX = 'MASKED_'
MIN_TOKEN_LENGTH = 3
# Paths to default name files:

# Regex to match an email address:
DEF_EMAIL_REGEX = (
    r"(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\""
    r"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")"
    r"@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5"
    r"[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|"
    r"[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\["
    r"\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"
)

EMAIL_REGEX = re.compile(DEF_EMAIL_REGEX)

ANONYMIZATION_KEY = 'adsacasdfafvab'

def anonymize(content: str) -> str:
    """Anonymize
    Anonymize content field from PII by using requester name.

    Args:
        ticket (str): String to anonymize.

    Returns:
        (list): List of all the tokens in the ticket
    """

    def process_token(token: str) -> str:
        """Anonymize token if in names or if email"""
        if len(token) < MIN_TOKEN_LENGTH:
            return token

        t = token.lower()
        # Removes punctuation from beginning and end of word:
        if t[0] in string.punctuation:
            t = t[1:]
        if t[-1] in string.punctuation:
            t = t[:-1]
        if EMAIL_REGEX.match(t):
            # logger.warn(f"ANONYMIZED!! {t}")
            return _anonymize_token(t)
        return token

    return ' '.join(process_token(t) for t in content.split())


def _anonymize_token(token: str) -> str:
    """Anonymize Token
    Receives a token to anonymize (like a name) and returns it's anonymized (hashed) version.
    Uses ANONYMIZATION_KEY defined in settings.py/env.py files.
    This function is a duplicate from Data Manager.

    Args:
        token (str): String to anonymize.

    Returns:
        str: Anonymized token.
    """
    string = f'{ANONYMIZATION_KEY}{token}'.encode('utf-8')
    return f"{PREFIX}{sha256(string).hexdigest()}"

FUNCTIONS = {'anonymize': anonymize}
