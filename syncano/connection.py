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
    :ivar api_key: Your Syncano ``Account Key`` or instance ``Api Key``
    :ivar user_key: Your Syncano ``User Key``
    :ivar instance_name: Your Syncano ``Instance Name``
    :ivar logger: Python logger instance
    :ivar timeout: Default request timeout
    :ivar verify_ssl: Verify SSL certificate
    """

    CONTENT_TYPE = 'application/json'

    AUTH_SUFFIX = 'v1/account/auth'
    USER_AUTH_SUFFIX = 'v1/instances/{name}/user/auth/'

    ADMIN_LOGIN_PARAMS = {'email', 'password'}
    ADMIN_ALT_LOGIN_PARAMS = {'api_key'}
    USER_LOGIN_PARAMS = {'username', 'password', 'api_key', 'instance_name'}
    USER_ALT_LOGIN_PARAMS = {'user_key', 'api_key', 'instance_name'}

    def __init__(self, host=None, **kwargs):
        self.host = host or syncano.API_ROOT
        self.logger = kwargs.get('logger', syncano.logger)
        self.timeout = kwargs.get('timeout', 30)
        # We don't need to check SSL cert in DEBUG mode
        self.verify_ssl = kwargs.pop('verify_ssl', True)

        self._init_login_params(kwargs)

        if self.is_user:
            self.AUTH_SUFFIX = self.USER_AUTH_SUFFIX.format(name=self.instance_name)
            self.auth_method = self.authenticate_user
        else:
            self.auth_method = self.authenticate_admin

        self.session = requests.Session()

    def _init_login_params(self, login_kwargs):

        def _set_value_or_default(param):
            param_lib_default_name = ''.join(param.split('_')).upper()
            value = login_kwargs.get(param, getattr(syncano, param_lib_default_name, None))
            setattr(self, param, value)

        map(_set_value_or_default, self.ADMIN_LOGIN_PARAMS.union(self.ADMIN_ALT_LOGIN_PARAMS,
                                                                 self.USER_LOGIN_PARAMS,
                                                                 self.USER_ALT_LOGIN_PARAMS))

    def _are_params_ok(self, params):
        return all(getattr(self, p) for p in params)

    @property
    def is_user(self):
        login_params_ok = self._are_params_ok(self.USER_LOGIN_PARAMS)
        alt_login_params_ok = self._are_params_ok(self.USER_ALT_LOGIN_PARAMS)
        return login_params_ok or alt_login_params_ok

    @property
    def is_alt_login(self):
        if self.is_user:
            return self._are_params_ok(self.USER_ALT_LOGIN_PARAMS)
        return self._are_params_ok(self.ADMIN_ALT_LOGIN_PARAMS)

    @property
    def auth_key(self):
        if self.is_user:
            return self.user_key
        return self.api_key

    def build_params(self, params):
        """
        :type params: dict
        :param params: Params which will be passed to request

        :rtype: dict
        :return: Request params
        """
        params = deepcopy(params)
        params['timeout'] = params.get('timeout', self.timeout)
        params['headers'] = params.get('headers', {})
        params['verify'] = self.verify_ssl

        if 'content-type' not in params['headers']:
            params['headers']['content-type'] = self.CONTENT_TYPE

        if self.is_user:
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
        is_auth = self.is_authenticated()
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
            # TODO(mk): quickfix - need to
            from datetime import datetime

            def to_native(value):
                if value is None:
                    return
                ret = value.isoformat()
                if ret.endswith('+00:00'):
                    ret = ret[:-6] + 'Z'

                if not ret.endswith('Z'):
                    ret = ret + 'Z'

                return ret

            for k, v in params['data'].iteritems():
                if isinstance(v, datetime):
                    params['data'][k] = to_native(v)
            #
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
        if self.is_user:
            return self.user_key is not None
        return self.api_key is not None

    def authenticate(self, **kwargs):
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
        is_auth = self.is_authenticated()

        if is_auth:
            msg = 'Connection already authenticated: {}'
        else:
            msg = 'Authentication successful: {}'
            self.logger.debug('Authenticating')
            self.auth_method(**kwargs)
        key = self.auth_key
        self.logger.debug(msg.format(key))
        return key

    def validate_params(self, kwargs):
        map_login_params = {
            (False, False): self.ADMIN_LOGIN_PARAMS,
            (True, False): self.ADMIN_ALT_LOGIN_PARAMS,
            (False, True): self.USER_LOGIN_PARAMS,
            (True, True): self.USER_ALT_LOGIN_PARAMS
        }

        for k in map_login_params[(self.is_alt_login, self.is_user)]:
            kwargs[k] = kwargs.get(k, getattr(self, k))

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
