import json
from copy import deepcopy

import requests
import six
import syncano
from syncano.exceptions import RevisionMismatchException, SyncanoRequestError, SyncanoValueError

if six.PY3:
    from urllib.parse import urljoin
else:
    from urlparse import urljoin


__all__ = ['Connection', 'ConnectionMixin']


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
    ACCOUNT_SUFFIX = 'v1/account/'
    SOCIAL_AUTH_SUFFIX = AUTH_SUFFIX + '/{social_backend}/'

    USER_AUTH_SUFFIX = 'v1/instances/{name}/user/auth/'
    USER_INFO_SUFFIX = 'v1/instances/{name}/user/'

    LOGIN_PARAMS = {'email',
                    'password'}
    ALT_LOGIN_PARAMS = {'api_key'}

    USER_LOGIN_PARAMS = {'username',
                         'password',
                         'api_key',
                         'instance_name'}
    USER_ALT_LOGIN_PARAMS = {'user_key',
                             'api_key',
                             'instance_name'}

    SOCIAL_LOGIN_PARAMS = {'token',
                           'social_backend'}

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
            if self.is_social:
                self.AUTH_SUFFIX = self.SOCIAL_AUTH_SUFFIX.format(social_backend=self.social_backend)
            self.auth_method = self.authenticate_admin

        self.session = requests.Session()

    def _init_login_params(self, login_kwargs):
        for param in self.LOGIN_PARAMS.union(self.ALT_LOGIN_PARAMS,
                                             self.USER_LOGIN_PARAMS,
                                             self.USER_ALT_LOGIN_PARAMS,
                                             self.SOCIAL_LOGIN_PARAMS):
            def_name = param.replace('_', '').upper()
            value = login_kwargs.get(param, getattr(syncano, def_name, None))
            setattr(self, param, value)

    def _are_params_ok(self, params):
        return all(getattr(self, p) for p in params)

    @property
    def is_user(self):
        login_params_ok = self._are_params_ok(self.USER_LOGIN_PARAMS)
        alt_login_params_ok = self._are_params_ok(self.USER_ALT_LOGIN_PARAMS)
        return login_params_ok or alt_login_params_ok

    @property
    def is_social(self):
        return self._are_params_ok(self.SOCIAL_LOGIN_PARAMS)

    @property
    def is_alt_login(self):
        if self.is_user:
            return self._are_params_ok(self.USER_ALT_LOGIN_PARAMS)
        return self._are_params_ok(self.ALT_LOGIN_PARAMS)

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
            params['headers']['Authorization'] = 'token {}'.format(self.api_key)

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
        data = kwargs.get('data', {})
        files = data.pop('files', None)

        self._check_batch_files(data)

        if files is None:
            files = {k: v for k, v in six.iteritems(data) if hasattr(v, 'read')}
            if data:
                kwargs['data'] = {k: v for k, v in six.iteritems(data) if k not in files}

        params = self.build_params(kwargs)
        method = getattr(self.session, method_name.lower(), None)

        # JSON dump can be expensive
        if syncano.DEBUG:
            debug_params = params.copy()
            debug_params.update({'files': [f for f in files]})  # show files in debug info;
            formatted_params = json.dumps(
                debug_params,
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
            params['files'] = self._process_apns_cert_files(files)

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
            if response.status_code == 400 and 'expected_revision' in content:
                raise RevisionMismatchException(response.status_code, content)
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

    def validate_params(self, kwargs, params):
        for k in params:
            kwargs[k] = kwargs.get(k, getattr(self, k))

            if kwargs[k] is None:
                raise SyncanoValueError('"{}" is required.'.format(k))
        return kwargs

    def authenticate_admin(self, **kwargs):
        if self.is_alt_login:
            request_args = self.validate_params(kwargs,
                                                self.ALT_LOGIN_PARAMS)
        else:
            if self.is_social:
                request_args = self.validate_params(kwargs,
                                                    self.SOCIAL_LOGIN_PARAMS)
                request_args['access_token'] = request_args.pop('token')  # core expects a access_token field;
            else:
                request_args = self.validate_params(kwargs,
                                                    self.LOGIN_PARAMS)

        response = self.make_request('POST', self.AUTH_SUFFIX, data=request_args)
        self.api_key = response.get('account_key')
        return self.api_key

    def authenticate_user(self, **kwargs):
        if self.is_alt_login:
            request_args = self.validate_params(kwargs,
                                                self.USER_ALT_LOGIN_PARAMS)
        else:
            request_args = self.validate_params(kwargs,
                                                self.USER_LOGIN_PARAMS)
        headers = {
            'content-type': self.CONTENT_TYPE,
            'X-API-KEY': request_args.pop('api_key')
        }
        response = self.make_request('POST', self.AUTH_SUFFIX, data=request_args, headers=headers)
        self.user_key = response.get('user_key')
        return self.user_key

    def get_account_info(self, api_key=None):
        self.api_key = api_key or self.api_key

        if not self.api_key:
            raise SyncanoValueError('api_key is required.')

        return self.make_request('GET', self.ACCOUNT_SUFFIX, headers={'X-API-KEY': self.api_key})

    def get_user_info(self, api_key=None, user_key=None):
        self.api_key = api_key or self.api_key
        self.user_key = user_key or self.user_key

        for attribute_name in ('api_key', 'user_key', 'instance_name'):
            if not getattr(self, attribute_name, None):
                raise SyncanoValueError('{attribute_name} is required.'.format(attribute_name=attribute_name))

        return self.make_request('GET', self.USER_INFO_SUFFIX.format(name=self.instance_name), headers={
            'X-API-KEY': self.api_key, 'X-USER-KEY': self.user_key})

    @classmethod
    def _check_batch_files(cls, data):
        if 'requests' in data:  # batch requests
            for request in data['requests']:
                per_request_files = request.get('body', {}).get('files', {})
                if per_request_files:
                    raise SyncanoValueError('Batch do not support files upload.')

    def _process_apns_cert_files(self, files):
        files = files.copy()
        for key in [file_name for file_name in files.keys()]:
            # remove certificates files (which are bool - True if cert exist, False otherwise)
            value = files[key]
            if isinstance(value, bool):
                files.pop(key)
                continue

            if key in ['production_certificate', 'development_certificate']:
                value = (value.name, value, 'application/x-pkcs12', {'Expires': '0'})
                files[key] = value
        return files


class ConnectionMixin(object):
    """Injects connection attribute with support of basic validation."""

    def __init__(self, *args, **kwargs):
        self._connection = None
        super(ConnectionMixin, self).__init__(*args, **kwargs)

    @property
    def connection(self):
        # Sometimes someone will not use super
        from syncano.models.registry import registry  # TODO: refactor this;
        return getattr(self, '_connection', None) or registry.connection()

    @connection.setter
    def connection(self, value):
        if not isinstance(value, Connection):
            raise SyncanoValueError('"connection" needs to be a Syncano Connection instance.')
        self._connection = value

    @connection.deleter
    def connection(self):
        self._connection = None
