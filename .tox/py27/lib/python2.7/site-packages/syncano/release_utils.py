# -*- coding: utf-8 -*-

import warnings
from functools import wraps

warnings.simplefilter('once')


class Deprecated(object):

    def __init__(self, lineno, removed_in_version):
        self.lineno = lineno  # how many decorators decorates the depracated func;
        self.removed_in_version = removed_in_version

    def __call__(self, original_func):
        @wraps(original_func)
        def new_func(*args, **kwargs):
            warnings.warn_explicit(
                message="Call to deprecated function '{}'. Will be removed in version: {}.".format(
                    original_func.__name__,
                    self.removed_in_version
                ),
                category=DeprecationWarning,
                filename=original_func.__code__.co_filename,
                lineno=original_func.__code__.co_firstlineno + self.lineno)
            return original_func(*args, **kwargs)
        return new_func
