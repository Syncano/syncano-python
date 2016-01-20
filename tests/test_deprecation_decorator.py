# -*- coding: utf-8 -*-
import unittest
import warnings

from syncano.release_utils import Deprecated


class DeprecationDecoratorTestCase(unittest.TestCase):

    def test_deprecation_decorator(self):

        class SomeClass(object):

            @Deprecated(lineno=0, removed_in_version='5.0.10')
            def some_deprecated_method(self):
                pass

        with warnings.catch_warnings(record=True) as warning:
            # Cause all warnings to always be triggered.
            warnings.simplefilter('always')
            # Trigger a warning.
            SomeClass().some_deprecated_method()
            # Verify some things
            self.assertEqual(len(warning), 1)
            self.assertEqual(warning[-1].category, DeprecationWarning)
            self.assertIn('deprecated', str(warning[-1].message))
            self.assertIn('5.0.10', str(warning[-1].message))
