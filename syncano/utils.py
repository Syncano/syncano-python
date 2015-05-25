import datetime
import re
from decimal import Decimal

import six
from slugify import slugify

PROTECTED_TYPES = six.integer_types + (
    type(None), float, Decimal, datetime.datetime,
    datetime.date, datetime.time)


def camelcase_to_underscore(text):
    """Converts camelcase text to underscore format."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def underscore_to_camelcase(text):
    """Converts underscore text to camelcase format."""
    text = text.replace('_', ' ').title()
    return text.replace(' ', '')


def get_class_name(*args):
    """Generates safe class name based on provided arguments."""
    name = '_'.join(args)
    name = slugify(name, separator='_')
    return underscore_to_camelcase(name)


def force_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    if isinstance(s, six.text_type):
        return s

    if strings_only and isinstance(s, PROTECTED_TYPES):
        return s

    try:
        if not isinstance(s, six.string_types):
            if six.PY3:
                if isinstance(s, bytes):
                    s = six.text_type(s, encoding, errors)
                else:
                    s = six.text_type(s)
            elif hasattr(s, '__unicode__'):
                s = six.text_type(s)
            else:
                s = six.text_type(bytes(s), encoding, errors)
        else:
            s = s.decode(encoding, errors)
    except UnicodeDecodeError:
        if not isinstance(s, Exception):
            raise
        s = ' '.join(force_text(arg, encoding, strings_only, errors)
                     for arg in s)
    return s
