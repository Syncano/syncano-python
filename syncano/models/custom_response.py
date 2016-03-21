import json

from syncano.exceptions import SyncanoException


class CustomResponseHandler(object):
    """
    A helper class which allows to define and maintain custom response handlers.

    Consider an example:
    Script code::

        set_response(HttpResponse(status_code=200, content='{"one": 1}', content_type='application/json'))

    When suitable ScriptTrace is used::

        trace = ScriptTrace.please.get(id=<code_box_trace_id>, script=<script_id>)

    Then trace object will have a content attribute, which will be a dict created from json (simple: json.loads under
      the hood);

    So this is possible::

        trace.content['one']

    And the trace.content is equal to::

        {'one': 1}

    The handler can be easily overwrite::

        def custom_handler(response):
            return json.loads(response['response']['content'])['one']

        trace.response_handler.overwrite_handler('application/json', custom_handler)

    or globally::

        ScriptTrace.response_handler.overwrite_handler('application/json', custom_handler)

    Then trace.content is equal to::
        1

    Currently supported content_types (but any handler can be defined):
      * application/json
      * text/plain

    """
    def __init__(self):
        self.handlers = {}
        self.register_handler('application/json', self.json_handler)
        self.register_handler('plain/text', self.plain_handler)

    def register_handler(self, content_type, handler):
        if content_type in self.handlers:
            raise SyncanoException('Handler "{}" already defined. User overwrite_handler instead.'.format(content_type))
        self.handlers[content_type] = handler

    def overwrite_handler(self, content_type, handler):
        if content_type not in self.handlers:
            raise SyncanoException('Handler "{}" not defined. User register_handler instead.'.format(content_type))
        self.handlers[content_type] = handler

    def process_response(self, response):
        content_type = self._find_content_type(response)
        try:
            return self.handlers[content_type](response)
        except KeyError:
            return self._default_handler(response)

    @staticmethod
    def _find_content_type(response):
        if not response:
            return None
        return response.get('response', {}).get('content_type')

    @staticmethod
    def _default_handler(response):
        if not response:
            return None

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


class CustomResponseMixin(object):
    """
    A mixin which extends the Script and ScriptEndpoint traces (and any other Model - if used) with following fields:
      * content - This is the response data if set_response is used in Script code, otherwise it is the 'stdout' field;
      * content_type - The content_type specified by the user in Script code;
      * status_code - The status_code specified by the user in Script code;
      * error - An error which can occur when code is executed: the stderr response field;

    To process the content based on content_type this Mixin uses the CustomResponseHandler - see the docs there.
    """

    response_handler = CustomResponseHandler()

    @property
    def content(self):
        return self.response_handler.process_response(self.result)

    @property
    def status_code(self):
        return self.result.get('response', {}).get('status') if self.result else None

    @property
    def error(self):
        return self.result.get('stderr') if self.result else None

    @property
    def content_type(self):
        return self.result.get('response', {}).get('content_type') if self.result else None
