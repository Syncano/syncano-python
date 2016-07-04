from syncano.exceptions import SyncanoRequestError, SyncanoValueError, UserNotFound

from . import fields
from .base import Model
from .classes import Class, DataObjectMixin, Object
from .instances import Instance
from .manager import ObjectManager


class Admin(Model):
    """
    OO wrapper around instance admins `link <http://docs.syncano.com/docs/administrators>`_.

    :ivar first_name: :class:`~syncano.models.fields.StringField`
    :ivar last_name: :class:`~syncano.models.fields.StringField`
    :ivar email: :class:`~syncano.models.fields.EmailField`
    :ivar role: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """
    ROLE_CHOICES = (
        {'display_name': 'full', 'value': 'full'},
        {'display_name': 'write', 'value': 'write'},
        {'display_name': 'read', 'value': 'read'},
    )

    first_name = fields.StringField(read_only=True, required=False)
    last_name = fields.StringField(read_only=True, required=False)
    email = fields.EmailField(read_only=True, required=False)
    role = fields.ChoiceField(choices=ROLE_CHOICES)
    links = fields.LinksField()

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['put', 'get', 'patch', 'delete'],
                'path': '/admins/{id}/',
            },
            'list': {
                'methods': ['get', 'post'],
                'path': '/admins/',
            }
        }


class Profile(DataObjectMixin, Object):
    """
    """

    PREDEFINED_CLASS_NAME = 'user_profile'

    PERMISSIONS_CHOICES = (
        {'display_name': 'None', 'value': 'none'},
        {'display_name': 'Read', 'value': 'read'},
        {'display_name': 'Write', 'value': 'write'},
        {'display_name': 'Full', 'value': 'full'},
    )

    owner = fields.IntegerField(label='owner id', required=False, read_only=True)
    owner_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    group = fields.IntegerField(label='group id', required=False)
    group_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    other_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    channel = fields.StringField(required=False)
    channel_room = fields.StringField(required=False, max_length=64)

    links = fields.LinksField()
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        parent = Class
        endpoints = {
            'detail': {
                'methods': ['delete', 'post', 'patch', 'get'],
                'path': '/objects/{id}/',
            },
            'list': {
                'methods': ['get', 'post'],
                'path': '/objects/',
            }
        }

    please = ObjectManager()


class User(Model):
    """
    OO wrapper around users `link <http://docs.syncano.com/docs/user-management>`_.

    :ivar username: :class:`~syncano.models.fields.StringField`
    :ivar password: :class:`~syncano.models.fields.StringField`
    :ivar user_key: :class:`~syncano.models.fields.StringField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    """

    username = fields.StringField(max_length=64, required=True)
    password = fields.StringField(read_only=False, required=True)
    user_key = fields.StringField(read_only=True, required=False)

    profile = fields.ModelField('Profile', read_only=False, default={},
                                just_pk=False, is_data_object_mixin=True)

    links = fields.LinksField()
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['delete', 'patch', 'put', 'get'],
                'path': '/users/{id}/',
            },
            'reset_key': {
                'methods': ['post'],
                'path': '/users/{id}/reset_key/',
            },
            'auth': {
                'methods': ['post'],
                'path': '/user/auth/',
            },
            'list': {
                'methods': ['get', 'post'],
                'path': '/users/',
            },
            'groups': {
                'methods': ['get', 'post', 'delete'],
                'path': '/users/{id}/groups/',
            }
        }

    def reset_key(self):
        properties = self.get_endpoint_data()
        http_method = 'POST'
        endpoint = self._meta.resolve_endpoint('reset_key', properties, http_method)
        connection = self._get_connection()
        return connection.request(http_method, endpoint)

    def auth(self, username=None, password=None):
        properties = self.get_endpoint_data()
        http_method = 'POST'
        endpoint = self._meta.resolve_endpoint('auth', properties, http_method)
        connection = self._get_connection()

        if not (username and password):
            raise SyncanoValueError('You need provide username and password.')

        data = {
            'username': username,
            'password': password
        }

        return connection.request(http_method, endpoint, data=data)

    def _user_groups_method(self, group_id=None, method='GET'):
        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('groups', properties, method)

        if group_id is not None and method != 'POST':
            endpoint += '{}/'.format(group_id)
        connection = self._get_connection()

        data = {}
        if method == 'POST':
            data = {'group': group_id}

        response = connection.request(method, endpoint, data=data)

        if method == 'DELETE':  # no response here;
            return

        if 'objects' in response:
            return [Group(**group_response['group']) for group_response in response['objects']]

        return Group(**response['group'])

    def add_to_group(self, group_id):
        return self._user_groups_method(group_id, method='POST')

    def list_groups(self):
        return self._user_groups_method()

    def group_details(self, group_id):
        return self._user_groups_method(group_id)

    def remove_from_group(self, group_id):
        return self._user_groups_method(group_id, method='DELETE')


class Group(Model):
    """
    OO wrapper around groups `link <http://docs.syncano.com/docs/groups>`_.

    :ivar label: :class:`~syncano.models.fields.StringField`
    :ivar description: :class:`~syncano.models.fields.StringField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    """

    label = fields.StringField(max_length=64, required=True)
    description = fields.StringField(read_only=False, required=False)

    links = fields.LinksField()
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['delete', 'patch', 'put', 'get'],
                'path': '/groups/{id}/',
            },
            'list': {
                'methods': ['get', 'post'],
                'path': '/groups/',
            },
            'users': {
                'methods': ['get', 'post', 'delete'],
                'path': '/groups/{id}/users/',
            }
        }

    def _group_users_method(self, user_id=None, method='GET'):
        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('users', properties, method)
        if user_id is not None and method != 'POST':
            endpoint += '{}/'.format(user_id)
        connection = self._get_connection()

        data = {}
        if method == 'POST':
            data = {'user': user_id}

        try:
            response = connection.request(method, endpoint, data=data)
        except SyncanoRequestError as e:
            if e.status_code == 404:
                raise UserNotFound(e.status_code, 'User not found.')
            raise

        if method == 'DELETE':
            return

        if 'objects' in response:
            return [User(**user_response['user']) for user_response in response['objects']]

        return User(**response['user'])

    def list_users(self):
        return self._group_users_method()

    def add_user(self, user_id):
        return self._group_users_method(user_id, method='POST')

    def user_details(self, user_id):
        return self._group_users_method(user_id)

    def delete_user(self, user_id):
        return self._group_users_method(user_id, method='DELETE')
