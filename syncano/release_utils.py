# -*- coding: utf-8 -*-

import warnings

warnings.simplefilter('default')


class Deprecated(object):

    def __init__(self, lineno, removed_in_version):
        self.lineno = lineno  # how many decorators decorates the depracated func;
        self.removed_in_version = removed_in_version

    def __call__(self, original_func):
        def new_func(*args, **kwargs):
            warnings.showwarning(
                message="Call to deprecated function '{}'. Will be removed in version: {}.".format(
                    original_func.__name__,
                    self.removed_in_version
                ),
                category=DeprecationWarning,
                filename=original_func.func_code.co_filename,
                lineno=original_func.func_code.co_firstlineno + self.lineno)
            return original_func(*args, **kwargs)
        return new_func
