

from . import fields
from .base import Model
from .mixins import RenameMixin


class Instance(RenameMixin, Model):
    """
    OO wrapper around instances `link <http://docs.syncano.com/docs/getting-started-with-syncano#adding-an-instance>`_.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar description: :class:`~syncano.models.fields.StringField`
    :ivar role: :class:`~syncano.models.fields.Field`
    :ivar owner: :class:`~syncano.models.fields.ModelField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar metadata: :class:`~syncano.models.fields.JSONField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar api_keys: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar users: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar admins: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar scripts: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar script_endpoints: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar templates: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar triggers: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar schedules: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar classes: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar invitations: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar gcm_devices: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar gcm_messages: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar apns_devices: :class:`~syncano.models.fields.RelatedManagerField`
    :ivar apns_messages: :class:`~syncano.models.fields.RelatedManagerField`
    """

    name = fields.StringField(max_length=64, primary_key=True)
    description = fields.StringField(read_only=False, required=False)
    role = fields.Field(read_only=True, required=False)
    owner = fields.ModelField('Admin', read_only=True)
    links = fields.LinksField()
    metadata = fields.JSONField(read_only=False, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    # user related fields;
    api_keys = fields.RelatedManagerField('ApiKey')
    users = fields.RelatedManagerField('User')
    admins = fields.RelatedManagerField('Admin')
    groups = fields.RelatedManagerField('Group')

    # snippets and data fields;
    scripts = fields.RelatedManagerField('Script')
    script_endpoints = fields.RelatedManagerField('ScriptEndpoint')
    templates = fields.RelatedManagerField('ResponseTemplate')

    triggers = fields.RelatedManagerField('Trigger')
    schedules = fields.RelatedManagerField('Schedule')
    classes = fields.RelatedManagerField('Class')
    invitations = fields.RelatedManagerField('InstanceInvitation')

    # push notifications fields;
    gcm_devices = fields.RelatedManagerField('GCMDevice')
    gcm_messages = fields.RelatedManagerField('GCMMessage')
    apns_devices = fields.RelatedManagerField('APNSDevice')
    apns_messages = fields.RelatedManagerField('APNSMessage')

    class Meta:
        endpoints = {
            'detail': {
                'methods': ['delete', 'patch', 'put', 'get'],
                'path': '/v1.1/instances/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/v1.1/instances/',
            }
        }


class ApiKey(Model):
    """
    OO wrapper around instance api keys `link <http://docs.syncano.com/docs/authentication>`_.

    :ivar api_key: :class:`~syncano.models.fields.StringField`
    :ivar allow_user_create: :class:`~syncano.models.fields.BooleanField`
    :ivar ignore_acl: :class:`~syncano.models.fields.BooleanField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """

    api_key = fields.StringField(read_only=True, required=False)
    description = fields.StringField(required=False)
    allow_user_create = fields.BooleanField(required=False, default=False)
    ignore_acl = fields.BooleanField(required=False, default=False)
    allow_anonymous_read = fields.BooleanField(required=False, default=False)
    links = fields.LinksField()

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
    OO wrapper around instance
    invitations `link <http://docs.syncano.com/docs/administrators#inviting-administrators>`_.

    :ivar email: :class:`~syncano.models.fields.EmailField`
    :ivar role: :class:`~syncano.models.fields.ChoiceField`
    :ivar key: :class:`~syncano.models.fields.StringField`
    :ivar state: :class:`~syncano.models.fields.StringField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    """
    from .accounts import Admin

    email = fields.EmailField(max_length=254)
    role = fields.ChoiceField(choices=Admin.ROLE_CHOICES)
    key = fields.StringField(read_only=True, required=False)
    state = fields.StringField(read_only=True, required=False)
    links = fields.LinksField()
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

    def resend(self):
        """
        Resend the invitation.
        :return: InstanceInvitation instance;
        """
        resend_path = self.links.resend
        connection = self._get_connection()
        connection.request('POST', resend_path)  # empty response here: 204 no content
        return self
