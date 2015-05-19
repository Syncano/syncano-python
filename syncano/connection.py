import json
from copy import deepcopy
from urlparse import urljoin

import requests
import six

import syncano
from syncano.exceptions import SyncanoRequestError, SyncanoValueError

__all__ = ['default_connection', 'Connection', 'ConnectionMixin']


def is_success(code):
    """Checks if response code is successful."""
    return 200 <= code <= 299


def is_client_error(code):
    """Checks if response code has client error."""
    return 400 <= code <= 499


def is_server_error(code):
    """Checks if response code has server error."""
    return 500 <= code <= 599


class DefaultConnection(object):
    """Singleton class which holds default connection."""

    def __init__(self):
        self._connection = None

    def __call__(self):
        if not self._connection:
            raise SyncanoValueError('Please open new connection.')
        return self._connection

    def open(self, *args, **kwargs):
        connection = Connection(*args, **kwargs)
        if not self._connection:
            self._connection = connection
        return connection


default_connection = DefaultConnection()


class Connection(object):
    """Base connection class.

    :ivar host: Syncano API host
    :ivar email: Your Syncano email address
    :ivar password: Your Syncano password
    :ivar api_key: Your Syncano ``Account Key``
    :ivar logger: Python logger instance
    :ivar timeout: Default request timeout
    :ivar verify_ssl: Verify SSL certificate
    """

    AUTH_SUFFIX = 'v1/account/auth'
    CONTENT_TYPE = 'application/json'

    def __init__(self, host=None, email=None, password=None, api_key=None, **kwargs):
        self.host = host or syncano.API_ROOT
        self.email = email or syncano.EMAIL
        self.password = password or syncano.PASSWORD
        self.api_key = api_key or syncano.APIKEY
        self.logger = kwargs.get('logger') or syncano.logger
        self.timeout = kwargs.get('timeout') or 30
        self.session = requests.Session()
        self.verify_ssl = kwargs.pop('verify_ssl', True)

    def build_params(self, params):
        """
        :type params: dict
        :param params: Params which will be passed to request

        :rtype: dict
        :return: Request params
        """
        params = deepcopy(params)
        params['timeout'] = params.get('timeout') or self.timeout
        params['headers'] = params.get('headers') or {}
        params['verify'] = True

        if 'content-type' not in params['headers']:
            params['headers']['content-type'] = self.CONTENT_TYPE

        if self.api_key and 'Authorization' not in params['headers']:
            params['headers']['Authorization'] = 'ApiKey %s' % self.api_key

        # We don't need to check SSL cert in DEBUG mode
        if syncano.DEBUG or not self.verify_ssl:
            params['verify'] = False

        return params

    def build_url(self, path):
        """Ensures proper format for provided path.

        :type path: string
        :param path: Request path

        :rtype: string
        :return: Request URL
        """
        if not isinstance(path, six.string_types):
            raise SyncanoValueError('"path" should be a string.')

        query = None

        if path.startswith(self.host):
            return path

        if '?' in path:
            path, query = path.split('?', 1)

        if not path.endswith('/'):
            path += '/'

        if path.startswith('/'):
            path = path[1:]

        if query:
            path = '{0}?{1}'.format(path, query)

        return urljoin(self.host, path)

    def request(self, method_name, path, **kwargs):
        """Simple wrapper around :func:`~syncano.connection.Connection.make_request` which
        will ensure that request is authenticated.

        :type method_name: string
        :param method_name: HTTP request method e.g: GET

        :type path: string
        :param path: Request path or full URL

        :rtype: dict
        :return: JSON response
        """

        if not self.is_authenticated():
            self.authenticate()

        return self.make_request(method_name, path, **kwargs)

    def make_request(self, method_name, path, **kwargs):
        """
        :type method_name: string
        :param method_name: HTTP request method e.g: GET

        :type path: string
        :param path: Request path or full URL

        :rtype: dict
        :return: JSON response

        :raises SyncanoValueError: if invalid request method was chosen
        :raises SyncanoRequestError: if something went wrong during the request
        """
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
            self.logger.debug('API Root: %s', self.host)
            self.logger.debug('Request: %s %s\n%s', method_name, path, formatted_params)

        if method is None:
            raise SyncanoValueError('Invalid request method: {0}.'.format(method_name))

        # Encode request payload
        if 'data' in params and not isinstance(params['data'], six.string_types):
            params['data'] = json.dumps(params['data'])

        url = self.build_url(path)
        response = method(url, **params)

        try:
            content = response.json()
        except ValueError:
            content = response.text

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

    def is_authenticated(self):
        """Checks if current session is authenticated.

        :rtype: boolean
        :return: Session authentication state
        """

        return self.api_key is not None

    def authenticate(self, email=None, password=None):
        """
        :type email: string
        :param email: Your Syncano account email address

        :type password: string
        :param password: Your Syncano password

        :rtype: string
        :return: Your ``Account Key``
        """

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


class ConnectionMixin(object):
    """Injects connection attribute with support of basic validation."""

    def __init__(self, *args, **kwargs):
        self._connection = None
        super(ConnectionMixin, self).__init__(*args, **kwargs)

    @property
    def connection(self):
        # Sometimes someone will not use super
        return getattr(self, '_connection', None) or default_connection()

    @connection.setter
    def connection(self, value):
        if not isinstance(value, Connection):
            raise SyncanoValueError('"connection" needs to be a Syncano Connection instance.')
        self._connection = value

    @connection.deleter
    def connection(self):
        self._connection = None
