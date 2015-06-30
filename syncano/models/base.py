from __future__ import unicode_literals

import inspect
import json
from copy import deepcopy

import six

from syncano.exceptions import SyncanoDoesNotExist, SyncanoValidationError
from syncano.utils import get_class_name

from . import fields
from .manager import CodeBoxManager, Manager, ObjectManager, WebhookManager
from .options import Options
from .registry import registry


class ModelMetaclass(type):
    """Metaclass for all models."""

    def __new__(cls, name, bases, attrs):
        super_new = super(ModelMetaclass, cls).__new__

        parents = [b for b in bases if isinstance(b, ModelMetaclass)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        module = attrs.pop('__module__', None)
        new_class = super_new(cls, name, bases, {'__module__': module})

        meta = attrs.pop('Meta', None) or getattr(new_class, 'Meta', None)
        meta = Options(meta)
        new_class.add_to_class('_meta', meta)

        manager = attrs.pop('please', Manager())
        new_class.add_to_class('please', manager)

        error_class = new_class.create_error_class()
        new_class.add_to_class('DoesNotExist', error_class)

        for n, v in six.iteritems(attrs):
            new_class.add_to_class(n, v)

        if not meta.pk:
            pk_field = fields.IntegerField(primary_key=True, read_only=True,
                                           required=False)
            new_class.add_to_class('id', pk_field)

        for field_name in meta.endpoint_fields:
            if field_name not in meta.field_names:
                endpoint_field = fields.EndpointField()
                new_class.add_to_class(field_name, endpoint_field)

        new_class.build_doc(name, meta)
        registry.add(name, new_class)
        return new_class

    def add_to_class(cls, name, value):
        if not inspect.isclass(value) and hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

    def create_error_class(cls):
        return type(
            str('{0}DoesNotExist'.format(cls.__name__)),
            (SyncanoDoesNotExist, ),
            {}
        )

    def build_doc(cls, name, meta):
        """Give the class a docstring if it's not defined."""
        if cls.__doc__ is not None:
            return

        field_names = ['{0} = {1}'.format(f.name, f.__class__.__name__) for f in meta.fields]
        cls.__doc__ = '{0}:\n\t{1}'.format(name, '\n\t'.join(field_names))


class Model(six.with_metaclass(ModelMetaclass)):
    """Base class for all models."""

    def __init__(self, **kwargs):
        self._raw_data = {}
        self.to_python(kwargs)

    def __repr__(self):
        """Displays current instance class name and pk."""
        return '<{0}: {1}>'.format(
            self.__class__.__name__,
            self.pk
        )

    def __str__(self):
        """Wrapper around ```repr`` method."""
        return repr(self)

    def __unicode__(self):
        """Wrapper around ```repr`` method with proper encoding."""
        return six.u(repr(self))

    def __eq__(self, other):
        if isinstance(other, Model):
            return self.pk == other.pk
        return NotImplemented

    def _get_connection(self, **kwargs):
        connection = kwargs.pop('connection', None)
        return connection or self._meta.connection

    def save(self, **kwargs):
        """
        Creates or updates the current instance.
        Override this in a subclass if you want to control the saving process.
        """
        self.validate()
        data = self.to_native()
        connection = self._get_connection(**kwargs)
        properties = self.get_endpoint_data()
        endpoint_name = 'list'
        method = 'POST'

        if not self.is_new():
            endpoint_name = 'detail'
            methods = self._meta.get_endpoint_methods(endpoint_name)
            if 'put' in methods:
                method = 'PUT'

        endpoint = self._meta.resolve_endpoint(endpoint_name, properties)
        request = {'data': data}
        response = connection.request(method, endpoint, **request)

        self.to_python(response)
        return self

    def delete(self, **kwargs):
        """Removes the current instance."""
        if self.is_new():
            raise SyncanoValidationError('Method allowed only on existing model.')

        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('detail', properties)
        connection = self._get_connection(**kwargs)
        connection.request('DELETE', endpoint)
        self._raw_data = {}

    def reload(self, **kwargs):
        """Reloads the current instance."""
        if self.is_new():
            raise SyncanoValidationError('Method allowed only on existing model.')

        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('detail', properties)
        connection = self._get_connection(**kwargs)
        response = connection.request('GET', endpoint)
        self.to_python(response)

    def validate(self):
        """
        Validates the current instance.

        :raises: SyncanoValidationError, SyncanoFieldError
        """
        for field in self._meta.fields:
            if not field.read_only:
                value = getattr(self, field.name)
                field.validate(value, self)

    def is_valid(self):
        try:
            self.validate()
        except SyncanoValidationError:
            return False
        else:
            return True

    def is_new(self):
        if 'links' in self._meta.field_names:
            return not self.links

        if self._meta.pk.read_only and not self.pk:
            return True

        return False

    def to_python(self, data):
        """
        Converts raw data to python types and built-in objects.

        :type data: dict
        :param data: Raw data
        """
        for field in self._meta.fields:
            if field.name in data:
                value = data[field.name]
                setattr(self, field.name, value)

    def to_native(self):
        """Converts the current instance to raw data which
        can be serialized to JSON and send to API."""
        data = {}
        for field in self._meta.fields:
            if not field.read_only and field.has_data:
                value = getattr(self, field.name)
                if not value and field.blank:
                    continue
                if field.mapping:
                    data[field.mapping] = field.to_native(value)
                else:
                    data[field.name] = field.to_native(value)
        return data

    def get_endpoint_data(self):
        properties = {}
        for field in self._meta.fields:
            if field.has_endpoint_data:
                properties[field.name] = getattr(self, field.name)
        return properties


class Coupon(Model):
    """
    OO wrapper around coupons `endpoint <TODO>`_.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar redeem_by: :class:`~syncano.models.fields.DateField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar percent_off: :class:`~syncano.models.fields.IntegerField`
    :ivar amount_off: :class:`~syncano.models.fields.FloatField`
    :ivar currency: :class:`~syncano.models.fields.ChoiceField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """

    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'redeem'},
    )
    CURRENCY_CHOICES = (
        {'display_name': 'USD', 'value': 'usd'},
    )

    name = fields.StringField(max_length=32, primary_key=True)
    redeem_by = fields.DateField()
    links = fields.HyperlinkedField(links=LINKS)
    percent_off = fields.IntegerField(required=False)
    amount_off = fields.FloatField(required=False)
    currency = fields.ChoiceField(choices=CURRENCY_CHOICES)
    duration = fields.IntegerField(default=0)

    class Meta:
        endpoints = {
            'detail': {
                'methods': ['get', 'delete'],
                'path': '/v1/billing/coupons/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/v1/billing/coupons/',
            }
        }


class Discount(Model):
    """
    OO wrapper around discounts `endpoint <TODO>`_.

    :ivar instance: :class:`~syncano.models.fields.ModelField`
    :ivar coupon: :class:`~syncano.models.fields.ModelField`
    :ivar start: :class:`~syncano.models.fields.DateField`
    :ivar end: :class:`~syncano.models.fields.DateField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """

    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    instance = fields.ModelField('Instance')
    coupon = fields.ModelField('Coupon')
    start = fields.DateField(read_only=True, required=False)
    end = fields.DateField(read_only=True, required=False)
    links = fields.HyperlinkedField(links=LINKS)

    class Meta:
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/v1/billing/discounts/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/v1/billing/discounts/',
            }
        }


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
    :ivar allow_user_create: :class:`~syncano.models.fields.StringField`
    :ivar ignore_acl: :class:`~syncano.models.fields.StringField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """
    LINKS = [
        {'type': 'detail', 'name': 'self'},
    ]

    api_key = fields.StringField(read_only=True, required=False)
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


class Class(Model):
    """
    OO wrapper around instance classes `endpoint <http://docs.syncano.com/v4.0/docs/instancesinstanceclasses>`_.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar description: :class:`~syncano.models.fields.StringField`
    :ivar objects_count: :class:`~syncano.models.fields.Field`
    :ivar schema: :class:`~syncano.models.fields.SchemaField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar status: :class:`~syncano.models.fields.Field`
    :ivar metadata: :class:`~syncano.models.fields.JSONField`
    :ivar revision: :class:`~syncano.models.fields.IntegerField`
    :ivar expected_revision: :class:`~syncano.models.fields.IntegerField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar group: :class:`~syncano.models.fields.IntegerField`
    :ivar group_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar other_permissions: :class:`~syncano.models.fields.ChoiceField`

    .. note::
        This model is special because each related :class:`~syncano.models.base.Object` will be
        **dynamically populated** with fields defined in schema attribute.
    """

    LINKS = [
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'objects'},
    ]

    PERMISSIONS_CHOICES = (
        {'display_name': 'None', 'value': 'none'},
        {'display_name': 'Read', 'value': 'read'},
        {'display_name': 'Create objects', 'value': 'create_objects'},
    )

    name = fields.StringField(max_length=64, primary_key=True)
    description = fields.StringField(read_only=False, required=False)
    objects_count = fields.Field(read_only=True, required=False)

    schema = fields.SchemaField(read_only=False, required=True)
    links = fields.HyperlinkedField(links=LINKS)
    status = fields.Field()
    metadata = fields.JSONField(read_only=False, required=False)

    revision = fields.IntegerField(read_only=True, required=False)
    expected_revision = fields.IntegerField(read_only=False, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)

    group = fields.IntegerField(label='group id', required=False)
    group_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    other_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')

    class Meta:
        parent = Instance
        plural_name = 'Classes'
        endpoints = {
            'detail': {
                'methods': ['get', 'put', 'patch', 'delete'],
                'path': '/classes/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/classes/',
            }
        }


class CodeBox(Model):
    """
    OO wrapper around codeboxes `endpoint <http://docs.syncano.com/v4.0/docs/codebox-list-codeboxes>`_.

    :ivar label: :class:`~syncano.models.fields.StringField`
    :ivar description: :class:`~syncano.models.fields.StringField`
    :ivar source: :class:`~syncano.models.fields.StringField`
    :ivar runtime_name: :class:`~syncano.models.fields.ChoiceField`
    :ivar config: :class:`~syncano.models.fields.Field`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`

    .. note::
        **CodeBox** has special method called ``run`` which will execute attached source code::

            >>> CodeBox.please.run('instance-name', 1234)
            >>> CodeBox.please.run('instance-name', 1234, payload={'variable_one': 1, 'variable_two': 2})
            >>> CodeBox.please.run('instance-name', 1234, payload="{\"variable_one\": 1, \"variable_two\": 2}")

        or via instance::

            >>> cb = CodeBox.please.get('instance-name', 1234)
            >>> cb.run()
            >>> cb.run(variable_one=1, variable_two=2)
    """

    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'runtimes'},
        # This will cause name collision between model run method
        # and HyperlinkedField dynamic methods.
        # {'type': 'detail', 'name': 'run'},
        {'type': 'detail', 'name': 'traces'},
    )
    RUNTIME_CHOICES = (
        {'display_name': 'nodejs', 'value': 'nodejs'},
        {'display_name': 'python', 'value': 'python'},
        {'display_name': 'ruby', 'value': 'ruby'},
    )

    label = fields.StringField(max_length=80)
    description = fields.StringField(required=False)
    source = fields.StringField()
    runtime_name = fields.ChoiceField(choices=RUNTIME_CHOICES)
    config = fields.Field(required=False)
    links = fields.HyperlinkedField(links=LINKS)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    please = CodeBoxManager()

    class Meta:
        parent = Instance
        name = 'Codebox'
        plural_name = 'Codeboxes'
        endpoints = {
            'detail': {
                'methods': ['put', 'get', 'patch', 'delete'],
                'path': '/codeboxes/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/codeboxes/',
            },
            'run': {
                'methods': ['post'],
                'path': '/codeboxes/{id}/run/',
            },
        }

    def run(self, **payload):
        """
        Usage::

            >>> cb = CodeBox.please.get('instance-name', 1234)
            >>> cb.run()
            >>> cb.run(variable_one=1, variable_two=2)
        """
        if self.is_new():
            raise SyncanoValidationError('Method allowed only on existing model.')

        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('run', properties)
        connection = self._get_connection(**payload)
        request = {
            'data': {
                'payload': json.dumps(payload)
            }
        }
        response = connection.request('POST', endpoint, **request)
        response.update({'instance_name': self.instance_name, 'codebox_id': self.id})
        return CodeBoxTrace(**response)


class CodeBoxTrace(Model):
    """
    :ivar status: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar executed_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar result: :class:`~syncano.models.fields.StringField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """

    STATUS_CHOICES = (
        {'display_name': 'Success', 'value': 'success'},
        {'display_name': 'Failure', 'value': 'failure'},
        {'display_name': 'Timeout', 'value': 'timeout'},
        {'display_name': 'Pending', 'value': 'pending'},
    )
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    status = fields.ChoiceField(choices=STATUS_CHOICES, read_only=True, required=False)
    links = fields.HyperlinkedField(links=LINKS)
    executed_at = fields.DateTimeField(read_only=True, required=False)
    result = fields.StringField(read_only=True, required=False)
    duration = fields.IntegerField(read_only=True, required=False)

    class Meta:
        parent = CodeBox
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/traces/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/traces/',
            }
        }


class Schedule(Model):
    """
    OO wrapper around codebox schedules `endpoint <http://docs.syncano.com/v4.0/docs/codebox-schedules-list>`_.

    :ivar label: :class:`~syncano.models.fields.StringField`
    :ivar codebox: :class:`~syncano.models.fields.IntegerField`
    :ivar interval_sec: :class:`~syncano.models.fields.IntegerField`
    :ivar crontab: :class:`~syncano.models.fields.StringField`
    :ivar payload: :class:`~syncano.models.fields.HyperliStringFieldnkedField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar scheduled_next: :class:`~syncano.models.fields.DateTimeField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """

    LINKS = [
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'traces'},
        {'type': 'list', 'name': 'codebox'},
    ]

    label = fields.StringField(max_length=80)
    codebox = fields.IntegerField(label='codebox id')
    interval_sec = fields.IntegerField(read_only=False, required=False)
    crontab = fields.StringField(max_length=40, required=False)
    payload = fields.StringField(required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)
    scheduled_next = fields.DateTimeField(read_only=True, required=False)
    links = fields.HyperlinkedField(links=LINKS)

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['put', 'get', 'patch', 'delete'],
                'path': '/schedules/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/schedules/',
            }
        }


class ScheduleTrace(Model):
    """
    :ivar status: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar executed_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar result: :class:`~syncano.models.fields.StringField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """

    STATUS_CHOICES = (
        {'display_name': 'Success', 'value': 'success'},
        {'display_name': 'Failure', 'value': 'failure'},
        {'display_name': 'Timeout', 'value': 'timeout'},
        {'display_name': 'Pending', 'value': 'pending'},
    )
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    status = fields.ChoiceField(choices=STATUS_CHOICES, read_only=True, required=False)
    links = fields.HyperlinkedField(links=LINKS)
    executed_at = fields.DateTimeField(read_only=True, required=False)
    result = fields.StringField(read_only=True, required=False)
    duration = fields.IntegerField(read_only=True, required=False)

    class Meta:
        parent = Schedule
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/traces/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/traces/',
            }
        }


class Admin(Model):
    """
    OO wrapper around instance admins `endpoint <http://docs.syncano.com/v4.0/docs/v1instancesinstanceadmins>`_.

    :ivar first_name: :class:`~syncano.models.fields.StringField`
    :ivar last_name: :class:`~syncano.models.fields.StringField`
    :ivar email: :class:`~syncano.models.fields.EmailField`
    :ivar role: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """

    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )
    ROLE_CHOICES = (
        {'display_name': 'full', 'value': 'full'},
        {'display_name': 'write', 'value': 'write'},
        {'display_name': 'read', 'value': 'read'},
    )

    first_name = fields.StringField(read_only=True, required=False)
    last_name = fields.StringField(read_only=True, required=False)
    email = fields.EmailField(read_only=True, required=False)
    role = fields.ChoiceField(choices=ROLE_CHOICES)
    links = fields.HyperlinkedField(links=LINKS)

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['put', 'get', 'patch', 'delete'],
                'path': '/admins/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/admins/',
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


class Object(Model):
    """
    OO wrapper around data objects `endpoint <http://docs.syncano.com/v4.0/docs/view-data-objects>`_.

    :ivar revision: :class:`~syncano.models.fields.IntegerField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar owner: :class:`~syncano.models.fields.IntegerField`
    :ivar owner_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar group: :class:`~syncano.models.fields.IntegerField`
    :ivar group_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar other_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar channel: :class:`~syncano.models.fields.StringField`
    :ivar channel_room: :class:`~syncano.models.fields.StringField`

    .. note::
        This model is special because each instance will be **dynamically populated**
        with fields defined in related :class:`~syncano.models.base.Class` schema attribute.
    """

    PERMISSIONS_CHOICES = (
        {'display_name': 'None', 'value': 'none'},
        {'display_name': 'Read', 'value': 'read'},
        {'display_name': 'Write', 'value': 'write'},
        {'display_name': 'Full', 'value': 'full'},
    )

    revision = fields.IntegerField(read_only=True, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    owner = fields.IntegerField(label='owner id', required=False, read_only=True)
    owner_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    group = fields.IntegerField(label='group id', required=False)
    group_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    other_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    channel = fields.StringField(required=False)
    channel_room = fields.StringField(required=False, max_length=64)

    please = ObjectManager()

    class Meta:
        parent = Class
        endpoints = {
            'detail': {
                'methods': ['delete', 'post', 'patch', 'get'],
                'path': '/objects/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/objects/',
            }
        }

    @staticmethod
    def __new__(cls, **kwargs):
        instance_name = kwargs.get('instance_name')
        class_name = kwargs.get('class_name')

        if not instance_name:
            raise SyncanoValidationError('Field "instance_name" is required.')

        if not class_name:
            raise SyncanoValidationError('Field "class_name" is required.')

        model = cls.get_subclass_model(instance_name, class_name)
        return model(**kwargs)

    @classmethod
    def create_subclass(cls, name, schema):
        attrs = {
            'Meta': deepcopy(Object._meta),
            '__new__': Model.__new__,  # We don't want to have maximum recursion depth exceeded error
        }

        for field in schema:
            field_type = field.get('type')
            field_class = fields.MAPPING[field_type]
            query_allowed = ('order_index' in field or 'filter_index' in field)
            attrs[field['name']] = field_class(required=False, read_only=False,
                                               query_allowed=query_allowed)

        return type(str(name), (Object, ), attrs)

    @classmethod
    def get_or_create_subclass(cls, name, schema):
        try:
            subclass = registry.get_model_by_name(name)
        except LookupError:
            subclass = cls.create_subclass(name, schema)
            registry.add(name, subclass)

        return subclass

    @classmethod
    def get_subclass_name(cls, instance_name, class_name):
        return get_class_name(instance_name, class_name, 'object')

    @classmethod
    def get_class_schema(cls, instance_name, class_name):
        parent = cls._meta.parent
        class_ = parent.please.get(instance_name, class_name)
        return class_.schema

    @classmethod
    def get_subclass_model(cls, instance_name, class_name, **kwargs):
        """
        Creates custom :class:`~syncano.models.base.Object` sub-class definition based
        on passed **instance_name** and **class_name**.
        """
        model_name = cls.get_subclass_name(instance_name, class_name)

        if cls.__name__ == model_name:
            return cls

        try:
            model = registry.get_model_by_name(model_name)
        except LookupError:
            schema = cls.get_class_schema(instance_name, class_name)
            model = cls.create_subclass(model_name, schema)
            registry.add(model_name, model)

        return model


class Trigger(Model):
    """
    OO wrapper around triggers `endpoint <http://docs.syncano.com/v4.0/docs/triggers-list>`_.

    :ivar label: :class:`~syncano.models.fields.StringField`
    :ivar codebox: :class:`~syncano.models.fields.IntegerField`
    :ivar klass: :class:`~syncano.models.fields.StringField`
    :ivar signal: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    """

    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'detail', 'name': 'codebox'},
        {'type': 'detail', 'name': 'klass'},
        {'type': 'detail', 'name': 'traces'},
    )
    SIGNAL_CHOICES = (
        {'display_name': 'post_update', 'value': 'post_update'},
        {'display_name': 'post_create', 'value': 'post_create'},
        {'display_name': 'post_delete', 'value': 'post_delete'},
    )

    label = fields.StringField(max_length=80)
    codebox = fields.IntegerField(label='codebox id')
    klass = fields.StringField(label='class name', mapping='class')
    signal = fields.ChoiceField(choices=SIGNAL_CHOICES)
    links = fields.HyperlinkedField(links=LINKS)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['put', 'get', 'patch', 'delete'],
                'path': '/triggers/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/triggers/',
            }
        }


class TriggerTrace(Model):
    """
    :ivar status: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar executed_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar result: :class:`~syncano.models.fields.StringField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """

    STATUS_CHOICES = (
        {'display_name': 'Success', 'value': 'success'},
        {'display_name': 'Failure', 'value': 'failure'},
        {'display_name': 'Timeout', 'value': 'timeout'},
        {'display_name': 'Pending', 'value': 'pending'},
    )
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    status = fields.ChoiceField(choices=STATUS_CHOICES, read_only=True, required=False)
    links = fields.HyperlinkedField(links=LINKS)
    executed_at = fields.DateTimeField(read_only=True, required=False)
    result = fields.StringField(read_only=True, required=False)
    duration = fields.IntegerField(read_only=True, required=False)

    class Meta:
        parent = Trigger
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/traces/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/traces/',
            }
        }


class Webhook(Model):
    """
    OO wrapper around webhooks `endpoint <http://docs.syncano.com/v4.0/docs/webhooks-list>`_.

    :ivar name: :class:`~syncano.models.fields.SlugField`
    :ivar codebox: :class:`~syncano.models.fields.IntegerField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`

    .. note::
        **WebHook** has special method called ``run`` which will execute related codebox::

            >>> Webhook.please.run('instance-name', 'webhook-name')
            >>> Webhook.please.run('instance-name', 'webhook-name', payload={'variable_one': 1, 'variable_two': 2})
            >>> Webhook.please.run('instance-name', 'webhook-name',
                                   payload="{\"variable_one\": 1, \"variable_two\": 2}")

        or via instance::

            >>> wh = Webhook.please.get('instance-name', 'webhook-name')
            >>> wh.run()
            >>> wh.run(variable_one=1, variable_two=2)

    """
    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'detail', 'name': 'codebox'},
    )

    name = fields.SlugField(max_length=50, primary_key=True)
    codebox = fields.IntegerField(label='codebox id')
    public = fields.BooleanField(required=False, default=False)
    public_link = fields.ChoiceField(required=False, read_only=True)
    links = fields.HyperlinkedField(links=LINKS)

    please = WebhookManager()

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['put', 'get', 'patch', 'delete'],
                'path': '/webhooks/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/webhooks/',
            },
            'run': {
                'methods': ['post'],
                'path': '/webhooks/{name}/run/',
            },
            'public': {
                'methods': ['get'],
                'path': 'webhooks/p/{public_link}/',
            }
        }

    def run(self, **payload):
        """
        Usage::

            >>> wh = Webhook.please.get('instance-name', 'webhook-name')
            >>> wh.run()
            >>> wh.run(variable_one=1, variable_two=2)
        """
        if self.is_new():
            raise SyncanoValidationError('Method allowed only on existing model.')

        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('run', properties)
        connection = self._get_connection(**payload)
        request = {
            'data': {
                'payload': json.dumps(payload)
            }
        }
        response = connection.request('POST', endpoint, **request)
        response.update({'instance_name': self.instance_name, 'webhook_name': self.name})
        return WebhookTrace(**response)


class WebhookTrace(Model):
    """
    :ivar status: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar executed_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar result: :class:`~syncano.models.fields.StringField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """

    STATUS_CHOICES = (
        {'display_name': 'Success', 'value': 'success'},
        {'display_name': 'Failure', 'value': 'failure'},
        {'display_name': 'Timeout', 'value': 'timeout'},
        {'display_name': 'Pending', 'value': 'pending'},
    )
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    status = fields.ChoiceField(choices=STATUS_CHOICES, read_only=True, required=False)
    links = fields.HyperlinkedField(links=LINKS)
    executed_at = fields.DateTimeField(read_only=True, required=False)
    result = fields.StringField(read_only=True, required=False)
    duration = fields.IntegerField(read_only=True, required=False)

    class Meta:
        parent = Webhook
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/traces/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/traces/',
            }
        }
