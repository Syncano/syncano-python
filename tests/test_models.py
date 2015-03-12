import unittest

try:
    from unittest import mock
except ImportError:
    import mock


class ModelTestCase(unittest.TestCase):
    pass


class CodeBoxTestCase(unittest.TestCase):

    def test_run(self):
        pass


class ObjectTestCase(unittest.TestCase):

    def test_create_subclass(self):
        pass

    def test_get_or_create_subclass(self):
        pass


class WebhookTestCase(unittest.TestCase):

    def test_run(self):
        pass
