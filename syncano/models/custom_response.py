import json


class CustomResponseHandler(object):

    def __init__(self):
        # a content_type -> handler method dict
        self.handlers = {}

    def register_handler(self, content_type, handler):
        self.handlers[content_type] = handler

    def process_response(self, response):
        content_type = self._find_content_type(response)
        try:
            return self.handlers[content_type](response)
        except KeyError:
            return self._default_handler(response)

    @staticmethod
    def _find_content_type(response):
        return response.get('response', {}).get('content_type')

    @staticmethod
    def _default_handler(response):
        if 'response' in response:
            return response['response']
        if 'stdout' in response:
            return response['stdout']

        return response

    @staticmethod
    def json_handler(response):
        return json.loads(response['response']['content'])

    @staticmethod
    def plain_handler(response):
        return response['response']['content']

custom_response_handler = CustomResponseHandler()
custom_response_handler.register_handler('application/json', CustomResponseHandler.json_handler)
custom_response_handler.register_handler('text/plain', CustomResponseHandler.plain_handler)


class CustomResponseMixin(object):

    @property
    def content(self):
        return custom_response_handler.process_response(self.result)

    @property
    def response_status(self):
        return self.result.get('response', {}).get('status')

    @property
    def error(self):
        return self.result.get('stderr')

    @property
    def content_type(self):
        return self.result.get('response', {}).get('content_type')
