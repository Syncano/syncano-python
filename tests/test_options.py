import unittest

from syncano.models.options import Options


class DummyMeta:
    _private_method = 1
    non_existing_method = 1
    plural_name = 'test'
    related_name = 'tests'


class OptionsTestCase(unittest.TestCase):

    def setUp(self):
        self.options = Options()

    def test_meta_inheritance(self):
        pass

    def test_build_properties(self):
        pass

    def test_contribute_to_class(self):
        pass

    def test_resolve_parent_data(self):
        pass

    def test_add_field(self):
        pass

    def test_get_field(self):
        pass

    def test_get_endpoint(self):
        pass

    def test_get_endpoint_properties(self):
        pass

    def test_get_endpoint_path(self):
        pass

    def test_get_endpoint_methods(self):
        pass

    def test_resolve_endpoint(self):
        pass

    def test_get_endpoint_query_params(self):
        pass

    def test_get_path_properties(self):
        pass