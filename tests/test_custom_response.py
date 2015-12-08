import json
import unittest

from syncano.models.custom_response import CustomResponseHandler


class ObjectTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.json_data = json.dumps({'one': 1, 'two': 2})

    def _wrap_data(self):
        return {'response': {'content': self.json_data, 'content_type': 'application/json'}}

    def test_default_json_handler(self):
        custom_handler = CustomResponseHandler()
        processed_data = custom_handler.process_response(self._wrap_data())

        self.assertDictEqual(processed_data, json.loads(self.json_data))

    def test_custom_json_handler(self):

        def json_custom_handler(response):
            #  return only two
            return json.loads(response['response']['content'])['two']

        custom_handler = CustomResponseHandler()
        custom_handler.overwrite_handler('application/json', json_custom_handler)

        processed_data = custom_handler.process_response(self._wrap_data())

        self.assertEqual(processed_data, json.loads(self.json_data)['two'])
