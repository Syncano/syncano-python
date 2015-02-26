import re

from slugify import slugify


def camelcase_to_underscore(text):
    """Converts camelcase text to underscore fromat."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def underscore_to_camelcase(text):
    """Converts underscore text to camelcase fromat."""
    text = text.replace('_', ' ').title()
    return text.replace(' ', '')


def get_class_name(*args):
    """Generates safe class name based on provided arguments."""
    name = '_'.join(args)
    name = slugify(name, separator='_')
    return underscore_to_camelcase(name)
