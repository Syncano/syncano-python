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
    USER_AUTH_SUFFIX = 'v1/instances/{name}/user/auth/'
    CONTENT_TYPE = 'application/json'

    def __init__(self, host=None, email=None, password=None, api_key=None, **kwargs):
        self.host = host or syncano.API_ROOT
        self.email = email or syncano.EMAIL
        self.password = password or syncano.PASSWORD

        self.api_key = api_key or syncano.APIKEY

        # instance indicates if we want to connect User or Admin
        self.instance_name = kwargs.get('instance_name')
        self.username = kwargs.get('username')
        self.user_key = kwargs.get('user_key')

        if self.api_key and self.instance_name:
            self.AUTH_SUFFIX = self.USER_AUTH_SUFFIX.format(name=self.instance_name)

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

        if self.user_key:
            params['headers'].update({
                'X-USER-KEY': self.user_key,
                'X-API-KEY': self.api_key
            })
        elif self.api_key and 'Authorization' not in params['headers']:
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
        is_auth, _ = self.is_authenticated()
        if not is_auth:
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
        files = kwargs.get('data', {}).pop('files', None)
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
        content = self.get_response_content(url, response)

        if files:
            # remove 'data' and 'content-type' to avoid "ValueError: Data must not be a string."
            params.pop('data')
            params['headers'].pop('content-type')
            params['files'] = files

            if response.status_code == 201:
                url = '{}{}/'.format(url, content['id'])

            patch = getattr(self.session, 'patch')
            # second request is needed to upload a file
            response = patch(url, **params)
            content = self.get_response_content(url, response)

        return content

    def get_response_content(self, url, response):
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
        if self.username and self.api_key:
            return self.user_key is not None, 'user'
        return self.api_key is not None, 'admin'

    def authenticate(self, email=None, username=None, password=None, api_key=None):
        """
        :type email: string
        :param email: Your Syncano account email address

        :type password: string
        :param password: Your Syncano password

        :type api_key: string
        :param api_key: Your Syncano api_key for instance

        :rtype: string
        :return: Your ``Account Key``
        """
        is_auth, who = self.is_authenticated()

        if is_auth:
            msg = 'Connection already authenticated for {0}: {1}'
            key = self.api_key

            if who == 'user':
                key = self.user_key

            self.logger.debug(msg.format(who, key))
            return key

        self.logger.debug('Authenticating: %s', email)

        if who == 'user':
            key = self.authenticate_user(username=username, password=password, api_key=api_key)
        else:
            key = self.authenticate_admin(email=email, password=password)

        self.logger.debug('Authentication successful for {0}: {1}'.format(who, key))
        return key

    def validate_params(self, kwargs):
        for k, v in kwargs.iteritems():
            kwargs[k] = v or getattr(self, k)

            if kwargs[k] is None:
                raise SyncanoValueError('"{}" is required.'.format(k))
        return kwargs

    def authenticate_admin(self, **kwargs):
        request_args = self.validate_params(kwargs)
        response = self.make_request('POST', self.AUTH_SUFFIX, data=request_args)
        self.api_key = response.get('account_key')
        return self.api_key

    def authenticate_user(self, **kwargs):
        request_args = self.validate_params(kwargs)
        headers = {
            'content-type': self.CONTENT_TYPE,
            'X-API-KEY': request_args.pop('api_key')
        }
        response = self.make_request('POST', self.AUTH_SUFFIX, data=request_args, headers=headers)
        self.user_key = response.get('user_key')
        return self.user_key


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
