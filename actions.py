
import re
import string
import phonenumbers
from hashlib import sha256

PREFIX = 'MASKED_'
MIN_TOKEN_LENGTH = 3
# Paths to default name files:

# Regex to match an email address:
EMAIL_REGEX = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
ANONYMIZATION_KEY = 'GO3fsF@WEB3DqWh'


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


def anonymize_emails(content: str, blacklisted_patterns: list) -> str:
    """Anonymize
    Anonymize all email addresses, except the ones matching any of the blacklisted patterns
    in content

    Args:
        content (str): String to anonymize.
        blacklisted_patterns (str): list of paterns to exclude from anaoymization

    Returns:
        (list): List of all the tokens in the ticket
    """
    for email in EMAIL_REGEX.findall(content):

        # if email address is blacklisted, continue to the next email address.
        if any(x.lower() in email.lower() for x in blacklisted_patterns):
            continue

        email = email.strip(string.punctuation)
        token = _anonymize_token(email)
        content = content.replace(email, token)

    return content


def anonymize_phone_numbers(content: str, blacklisted_patterns: list) -> str:
    """Anonymize_phone_numbers
    Detects and replaces phone numbers with a anonymizaion token
    Args:
        content (str): String to anonymize.

    Returns:
        str: Anonymized String
    """
    for match in phonenumbers.PhoneNumberMatcher(content, "US"):

        # If number is blacklisted, continue to the next number
        if any(x.lower() in match.raw_string for x in blacklisted_patterns):
            continue

        token = _anonymize_token(match.raw_string)
        content = content.replace(match.raw_string, token)
    return content


###############################################################################################
# Add your custom functions here. When done, add your function to "FUNCTIONS" dictionary      #
###############################################################################################


FUNCTIONS = {
    'anonymize_emails': anonymize_emails,
    'anonymize_phone_numbers': anonymize_phone_numbers
}
