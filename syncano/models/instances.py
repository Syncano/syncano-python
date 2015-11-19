from __future__ import unicode_literals

from . import fields
from .base import Model


class Instance(Model):
    """
    OO wrapper around instances `endpoint <http://docs.syncano.com/v4.0/docs/instances>`_.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar description: :class:`~syncano.models.fields.StringField`
    :ivar role: :class:`~syncano.models.fields.Field`
    :ivar owner: :class:`~syncano.models.fields.ModelField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar metadata: :class:`~syncano.models.fields.JSONField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    """

    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'admins'},
        {'type': 'list', 'name': 'classes'},
        {'type': 'list', 'name': 'codeboxes'},
        {'type': 'list', 'name': 'invitations'},
        {'type': 'list', 'name': 'runtimes'},
        {'type': 'list', 'name': 'api_keys'},
        {'type': 'list', 'name': 'triggers'},
        {'type': 'list', 'name': 'users'},
        {'type': 'list', 'name': 'webhooks'},
        {'type': 'list', 'name': 'schedules'},
    )

    name = fields.StringField(max_length=64, primary_key=True)
    description = fields.StringField(read_only=False, required=False)
    role = fields.Field(read_only=True, required=False)
    owner = fields.ModelField('Admin', read_only=True)
    links = fields.HyperlinkedField(links=LINKS)
    metadata = fields.JSONField(read_only=False, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        endpoints = {
            'detail': {
                'methods': ['delete', 'patch', 'put', 'get'],
                'path': '/v1/instances/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/v1/instances/',
            }
        }


class ApiKey(Model):
    """
    OO wrapper around instance api keys `endpoint <TODO>`_.

    :ivar api_key: :class:`~syncano.models.fields.StringField`
    :ivar allow_user_create: :class:`~syncano.models.fields.BooleanField`
    :ivar ignore_acl: :class:`~syncano.models.fields.BooleanField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """
    LINKS = [
        {'type': 'detail', 'name': 'self'},
    ]

    api_key = fields.StringField(read_only=True, required=False)
    description = fields.StringField(required=False)
    allow_user_create = fields.BooleanField(required=False, default=False)
    ignore_acl = fields.BooleanField(required=False, default=False)
    links = fields.HyperlinkedField(links=LINKS)

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['get', 'delete'],
                'path': '/api_keys/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/api_keys/',
            }
        }


class InstanceInvitation(Model):
    """
    OO wrapper around instance invitations
    `endpoint <http://docs.syncano.com/v4.0/docs/list-administrator-invitations>`_.

    :ivar email: :class:`~syncano.models.fields.EmailField`
    :ivar role: :class:`~syncano.models.fields.ChoiceField`
    :ivar key: :class:`~syncano.models.fields.StringField`
    :ivar state: :class:`~syncano.models.fields.StringField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    """
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )
    from .accounts import Admin

    email = fields.EmailField(max_length=254)
    role = fields.ChoiceField(choices=Admin.ROLE_CHOICES)
    key = fields.StringField(read_only=True, required=False)
    state = fields.StringField(read_only=True, required=False)
    links = fields.HyperlinkedField(links=LINKS)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        parent = Instance
        name = 'Invitation'
        endpoints = {
            'detail': {
                'methods': ['get', 'delete'],
                'path': '/invitations/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/invitations/',
            }
        }
