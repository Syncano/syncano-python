# -*- coding: utf-8 -*-

from syncano.exceptions import SyncanoValueError
from tests.integration_test import InstanceMixin, IntegrationTest


class SnippetConfigTest(InstanceMixin, IntegrationTest):

    def test_update_config(self):
        config = {
            'num': 123,
            'foo': 'bar',
            'arr': [1, 2, 3, 4],
            'another': {
                'num': 123,
                'foo': 'bar',
                'arr': [1, 2, 3, 4]
            }
        }
        self.instance.set_config(config)
        saved_config = self.instance.get_config()
        self.assertDictContainsSubset(config, saved_config, 'Retrieved config should be equal to saved config.')

    def test_update_invalid_config(self):
        with self.assertRaises(SyncanoValueError):
            self.instance.set_config('invalid config')
        with self.assertRaises(SyncanoValueError):
            self.instance.set_config([1, 2, 3])

    def test_update_existing_config(self):
        config = {
            'foo': 'bar'
        }
        self.instance.set_config(config)
        saved_config = self.instance.get_config()
        self.assertIn('foo', saved_config, 'Retrieved config should contain saved key.')
        new_config = {
            'new_foo': 'new_bar'
        }
        self.instance.set_config(new_config)
        saved_config = self.instance.get_config()
        self.assertDictContainsSubset(new_config, saved_config, 'Retrieved config should be equal to saved config.')
        self.assertNotIn('foo', saved_config, 'Retrieved config should not contain old keys.')
