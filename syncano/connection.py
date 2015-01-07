import json
import requests
from urlparse import urljoin
from copy import deepcopy

import syncano
from syncano.exceptions import (
    SyncanoValueError, SyncanoRequestError,
)
from syncano.resultset import ResultSet


class Connection(object):
    AUTH_SUFFIX = '/account/auth/'
    CONTENT_TYPE = 'application/json'
    RESULT_SET_CLASS = ResultSet

    def __init__(self, host, email=None, password=None, api_key=None, **kwargs):
        self.host = host or syncano.API_ROOT
        self.email = email
        self.password = password
        self.api_key = api_key
        self.logger = kwargs.get('logger') or syncano.logger
        self.timeout = kwargs.get('timeout') or 30
        self.session = requests.Session()

    def build_params(self, kwargs):
        params = deepcopy(kwargs)
        params['timeout'] = params.get('timeout') or self.timeout
        params['headers'] = params.get('headers') or {}

        if 'content-type' not in params['headers']:
            params['headers']['content-type'] = self.CONTENT_TYPE

        if self.api_key and 'Authorization' not in params['headers']:
            params['headers']['Authorization'] = 'ApiKey %s' % self.api_key

        if 'data' in params and not isinstance(params['data'], (str, unicode)):
            params['data'] = json.dumps(params['data'])

        return params

    def make_request(self, method_name, url, **kwargs):
        if not self.api_key:
            self.authenticate()

        self.logger.debug('Request: %s', url)

        params = self.build_params(kwargs)
        method = getattr(self.session, method_name.lower(), None)

        if method is None:
            raise SyncanoValueError('Invalid request method: {0}'.format(method_name))

        response = method(url, **params)
        has_json = response.headers.get('content-type') == 'application/json'
        content = response.json() if has_json else response.text

        if response.status_code not in [200, 201]:
            content = content['detail'] if has_json else content
            self.logger.debug('Request Error: %s', url)
            self.logger.debug('Status code: %d', response.status_code)
            self.logger.debug('Response: %s', content)
            raise SyncanoRequestError(response.status_code, content)

        return content

    def authenticate(self, email=None, password=None):
        if self.api_key:
            self.logger.debug('Connection already authenticated: %s', self.api_key)
            return self.api_key

        email = email or self.email
        password = password or self.password

        if not email:
            raise SyncanoValueError('"email" is required')

        if not password:
            raise SyncanoValueError('"password" is required')

        self.logger.debug('Authenticating: %s', email)

        url = urljoin(self.host, self.AUTH_SUFFIX)
        data = {'email': email, 'password': password}
        response = self.make_request('POST', url, data=data)
        account_key = response.get('account_key')
        self.api_key = account_key

        self.logger.debug('Authenticated: %s', email)
        return account_key
