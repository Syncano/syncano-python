import json
import requests
import six
from urlparse import urljoin
from copy import deepcopy

import syncano
from syncano.exceptions import SyncanoValueError, SyncanoRequestError
from syncano.models import Registry


def is_success(code):
    return code >= 200 and code <= 299


def is_client_error(code):
    return code >= 400 and code <= 499


def is_server_error(code):
    return code >= 500 and code <= 599


class Connection(object):
    AUTH_SUFFIX = 'v1/account/auth'
    SCHEMA_SUFFIX = 'v1/schema'
    CONTENT_TYPE = 'application/json'

    def __init__(self, host=None, email=None, password=None, api_key=None, **kwargs):
        self.host = host or syncano.API_ROOT
        self.email = email
        self.password = password
        self.api_key = api_key
        self.logger = kwargs.get('logger') or syncano.logger
        self.timeout = kwargs.get('timeout') or 30
        self.session = requests.Session()
        self.models = Registry(self).register_schema(self.schema)

    def build_params(self, params):
        params = deepcopy(params)
        params['timeout'] = params.get('timeout') or self.timeout
        params['headers'] = params.get('headers') or {}

        if 'content-type' not in params['headers']:
            params['headers']['content-type'] = self.CONTENT_TYPE

        if self.api_key and 'Authorization' not in params['headers']:
            params['headers']['Authorization'] = 'ApiKey %s' % self.api_key

        # We don't need to check SSL cert in DEBUG mode
        if syncano.DEBUG:
            params['verify'] = False

        return params

    def build_url(self, path):
        if not isinstance(path, six.string_types):
            raise SyncanoValueError('"path" should be a string.')

        if path.startswith(self.host):
            return path

        if not path.endswith('/'):
            path += '/'

        if path.startswith('/'):
            path = path[1:]

        return urljoin(self.host, path)

    def request(self, method_name, path, **kwargs):
        '''Simple wrapper around make_request which
        will ensure that request is authenticated.'''

        if not self.is_authenticated():
            self.authenticate()

        return self.make_request(method_name, path, **kwargs)

    def make_request(self, method_name, path, **kwargs):
        params = self.build_params(kwargs)
        method = getattr(self.session, method_name.lower(), None)

        # JSON dump can be expensive
        if syncano.DEBUG:
            formatted_params = json.dumps(
                params,
                sort_keys=True,
                indent=2,
                separators=(',', ': ')
            )
            self.logger.debug('Request: %s %s\n%s', method_name, path, formatted_params)

        if method is None:
            raise SyncanoValueError('Invalid request method: {0}.'.format(method_name))

        # Encode request payload
        if 'data' in params and not isinstance(params['data'], six.string_types):
            params['data'] = json.dumps(params['data'])

        url = self.build_url(path)
        response = method(url, **params)
        content = response.json()

        if is_server_error(response.status_code):
            raise SyncanoRequestError(response.status_code, 'Server error.')

        # Validation error
        if is_client_error(response.status_code):
            raise SyncanoRequestError(response.status_code, content)

        # Other errors
        if not is_success(response.status_code):
            self.logger.debug('Request Error: %s', url)
            self.logger.debug('Status code: %d', response.status_code)
            self.logger.debug('Response: %s', content)
            raise SyncanoRequestError(response.status_code, content)

        return content

    @property
    def schema(self):
        if not hasattr(self, '_schema'):
            response = self.make_request('GET', self.SCHEMA_SUFFIX)
            self._schema = response
        return self._schema

    def is_authenticated(self):
        return self.api_key is not None

    def authenticate(self, email=None, password=None):
        if self.is_authenticated():
            self.logger.debug('Connection already authenticated: %s', self.api_key)
            return self.api_key

        email = email or self.email
        password = password or self.password

        if not email:
            raise SyncanoValueError('"email" is required.')

        if not password:
            raise SyncanoValueError('"password" is required.')

        self.logger.debug('Authenticating: %s', email)

        data = {'email': email, 'password': password}
        response = self.make_request('POST', self.AUTH_SUFFIX, data=data)
        account_key = response.get('account_key')
        self.api_key = account_key

        self.logger.debug('Authentication successful: %s', account_key)
        return account_key
