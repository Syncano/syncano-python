from __future__ import unicode_literals

import six
import inspect

from syncano.exceptions import SyncanoValidationError, SyncanoDoesNotExist
from . import fields
from .options import Options
from .manager import Manager
from .registry import registry


class ModelMetaclass(type):

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

        if not meta._pk:
            pk_field = fields.IntegerField(primary_key=True, read_only=True,
                                           required=False)
            new_class.add_to_class('id', pk_field)

        for field_name in meta.endpoint_fields:
            if field_name not in meta.field_names:
                endpoint_field = fields.EndpointField()
                new_class.add_to_class(field_name, endpoint_field)

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


class Model(six.with_metaclass(ModelMetaclass)):

    def __init__(self, **kwargs):
        self._raw_data = {}
        self.to_python(kwargs)

    def __repr__(self):
        return '<{0}: {1}>'.format(
            self.__class__.__name__,
            self.pk
        )

    @property
    def connection(self, **kwargs):
        connection = kwargs.pop('connection', None)
        return connection or self._meta.connection

    def save(self, **kwargs):
        self.validate()
        data = self.to_native()
        connection = self._get_connection(**kwargs)

        if self.links:
            endpoint = self.links['self']
            method = 'PUT'
        else:
            properties = self.get_endpoint_data()
            endpoint = self._meta.resolve_endpoint('list', properties)
            method = 'POST'

        request = {'data': data}
        response = connection.request(method, endpoint, **request)

        self.to_python(response)
        return self

    def delete(self, **kwargs):
        if not self.links:
            raise SyncanoValidationError('Method allowed only on existing model.')

        endpoint = self.links['self']
        connection = self._get_connection(**kwargs)
        connection.request('DELETE', endpoint)
        self._raw_data = {}

    def validate(self):
        for field in self._meta.fields:
            if not field.read_only:
                value = getattr(self, field.name)
                field.validate(value, self)

    def is_valid(self):
        try:
            self.validate()
            return True
        except SyncanoValidationError:
            return False

    def to_python(self, data):
        for field in self._meta.fields:
            if field.name in data:
                value = data[field.name]
                setattr(self, field.name, value)

    def to_native(self):
        data = {}
        for field in self._meta.fields:
            if not field.read_only and field.has_data:
                value = getattr(self, field.name)
                data[field.name] = field.to_native(value)
        return data

    def get_endpoint_data(self):
        properties = {}
        for field in self._meta.fields:
            if field.has_endpoint_data:
                properties[field.name] = getattr(self, field.name)
        return properties


class ApiKey(Model):
    LINKS = [
        {'type': 'detail', 'name': 'self'},
    ]

    api_key = fields.Field()
    links = fields.HyperlinkedField(links=LINKS)

    class Meta:
        endpoints = {
            'detail': {
                'methods': ['get', 'delete'],
                'path': '/v1/instances/{instance_name}/api_keys/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/v1/instances/{instance_name}/api_keys/',
            }
        }


class Balance(Model):

    class Meta:
        endpoints = {
            'list': {
                'methods': ['get'],
                'path': '/v1/billing/balance/',
            }
        }


class Class(Model):
    LINKS = [
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'objects'},
    ]

    name = fields.StringField(max_length=64, primary_key=True)
    color = fields.StringField(read_only=False, min_length=7, required=False, max_length=7)
    description = fields.StringField(read_only=False, required=False)
    objects_count = fields.Field(read_only=True, required=False)
    icon = fields.StringField(read_only=False, max_length=40, required=False)
    revision = fields.IntegerField(read_only=True, required=True)
    schema = fields.Field(read_only=False, required=True)
    links = fields.HyperlinkedField(links=LINKS)
    status = fields.Field()
    updated_at = fields.DateTimeField(read_only=True, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["delete", "post", "patch", "get"],
                "path": "/v1/instances/{instance_name}/classes/{name}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/instances/{instance_name}/classes/",
            }
        }


class CodeBoxSchedule(Model):
    LINKS = [
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'traces'},
    ]

    links = fields.HyperlinkedField(read_only=True, required=False, links=LINKS)
    scheduled_next = fields.DateTimeField(read_only=True, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)
    interval_sec = fields.IntegerField(read_only=False, required=False)
    crontab = fields.StringField(read_only=False, max_length=40, required=False)
    payload = fields.StringField(read_only=False, required=False)

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["get", "delete"],
                "path": "/v1/instances/{instance_name}/codeboxes/{codebox_id}/schedules/{id}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/instances/{instance_name}/codeboxes/{codebox_id}/schedules/",
            }
        }


class CodeBoxTrace(Model):
    STATUS_CHOICES = (
        {'display_name': 'Success', 'value': 'success'},
        {'display_name': 'Failure', 'value': 'failure'},
        {'display_name': 'Timeout', 'value': 'timeout'},
    )
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    status = fields.ChoiceField(read_only=False, choices=STATUS_CHOICES, required=True)
    links = fields.HyperlinkedField(read_only=True, required=False, links=LINKS)
    executed_at = fields.DateTimeField(read_only=False, required=True)
    result = fields.StringField(read_only=False, required=False)
    duration = fields.IntegerField(read_only=False, required=True)

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["get"],
                "path": "/v1/instances/{instance_name}/codeboxes/{codebox_id}/schedules/{schedule_id}/traces/{id}/",
            },
            "list": {
                "methods": ["get"],
                "path": "/v1/instances/{instance_name}/codeboxes/{codebox_id}/schedules/{schedule_id}/traces/",
            }
        }


class CodeBox(Model):
    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'schedules'},
        {'type': 'list', 'name': 'runtimes'},
    )
    RUNTIME_CHOICES = (
        {'display_name': 'nodejs', 'value': 'nodejs'},
        {'display_name': 'python', 'value': 'python'},
        {'display_name': 'ruby', 'value': 'ruby'},
    )

    description = fields.StringField(required=False)
    links = fields.HyperlinkedField(links=LINKS)
    source = fields.StringField()
    runtime_name = fields.ChoiceField(choices=RUNTIME_CHOICES)
    config = fields.Field(required=False)
    name = fields.StringField(max_length=80)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["put", "get", "patch", "delete"],
                "path": "/v1/instances/{instance_name}/codeboxes/{id}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/instances/{instance_name}/codeboxes/",
            }
        }


class Coupon(Model):
    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'redeem'},
    )
    CURRENCY_CHOICES = (
        {'display_name': 'USD', 'value': 'usd'},
    )

    name = fields.StringField(max_length=32, primary_key=True)
    percent_off = fields.IntegerField(required=False)
    redeem_by = fields.DateField()
    links = fields.HyperlinkedField(links=LINKS)
    amount_off = fields.FloatField(required=False)
    currency = fields.ChoiceField(choices=CURRENCY_CHOICES)
    duration = fields.IntegerField()

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["get", "delete"],
                "path": "/v1/billing/coupons/{name}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/billing/coupons/",
            }
        }


class Discount(Model):
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    end = fields.DateField(read_only=True, required=True, label='end')
    links = fields.HyperlinkedField(read_only=True, required=False, links=LINKS)
    start = fields.DateField(read_only=True, required=False, label='start')
    coupon = fields.Field()
    instance = fields.Field()

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["get"],
                "path": "/v1/billing/discounts/{id}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/billing/discounts/",
            }
        }


class Info(Model):

    class Meta:
        endpoints = {
            "list": {
                "methods": ["get"],
                "path": "/v1/billing/info/",
            }
        }


class InstanceAdmin(Model):
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )
    ROLE_CHOICES = (
        {'display_name': 'full', 'value': 'full'},
        {'display_name': 'write', 'value': 'write'},
        {'display_name': 'read', 'value': 'read'},
    )

    first_name = fields.Field(read_only=True, required=False)
    last_name = fields.Field(read_only=True, required=False)
    links = fields.HyperlinkedField(links=LINKS)
    email = fields.Field(read_only=True, required=False)
    role = fields.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["put", "get", "patch", "delete"],
                "path": "/v1/instances/{instance_name}/admins/{id}/",
            },
            "list": {
                "methods": ["get"],
                "path": "/v1/instances/{instance_name}/admins/",
            }
        }


class Instance(Model):
    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'list', 'name': 'admins'},
        {'type': 'list', 'name': 'classes'},
        {'type': 'list', 'name': 'codeboxes'},
        {'type': 'list', 'name': 'codebox_runtimes'},
        {'type': 'list', 'name': 'invitations'},
        {'type': 'list', 'name': 'api_keys'},
        {'type': 'list', 'name': 'triggers'},
        {'type': 'list', 'name': 'webhooks'},
    )

    name = fields.StringField(read_only=False, max_length=64, required=True, primary_key=True)
    links = fields.HyperlinkedField(read_only=True, required=False, links=LINKS)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)
    role = fields.Field(read_only=True, required=False)
    owner = fields.Field()
    description = fields.StringField(read_only=False, required=False)

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["delete", "post", "patch", "get"],
                "path": "/v1/instances/{name}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/instances/",
            }
        }


class Invitation(Model):
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    links = fields.HyperlinkedField(links=LINKS)
    created_at = fields.DateTimeField(read_only=True, required=False, label='created at')
    email = fields.EmailField(read_only=False, max_length=254, required=True, label='email')
    role = fields.Field(read_only=True, required=False)
    key = fields.StringField(read_only=False, max_length=40, required=True, label='key')

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["put", "get", "patch", "delete"],
                "path": "/v1/instances/{instance_name}/invitations/{id}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/instances/{instance_name}/invitations/",
            }
        }


class Invoice(Model):

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["get"],
                "path": "/v1/billing/invoices/{id}/",
            },
            "list": {
                "methods": ["get"],
                "path": "/v1/billing/invoices/",
            }
        }


class Object(Model):
    created_at = fields.DateTimeField(read_only=True, required=False, label='created at')
    revision = fields.IntegerField(read_only=True, required=True, label='revision')
    updated_at = fields.DateTimeField(read_only=True, required=False, label='updated at')

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["delete", "post", "patch", "get"],
                "path": "/v1/instances/{instance_name}/classes/{class_name}/objects/{id}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/instances/{instance_name}/classes/{class_name}/objects/",
            }
        }


class Runtime(Model):

    class Meta:
        endpoints = {
            "list": {
                "methods": ["get"],
                "path": "/v1/instances/{instance_name}/codeboxes/runtimes/",
            }
        }


class Trigger(Model):
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )
    SIGNAL_CHOICES = (
        {'display_name': 'post_update', 'value': 'post_update'},
        {'display_name': 'post_create', 'value': 'post_create'},
        {'display_name': 'post_delete', 'value': 'post_delete'},
    )

    codebox = fields.Field(read_only=False, required=True, label='codebox')
    links = fields.HyperlinkedField(read_only=True, required=False, links=LINKS)
    created_at = fields.DateTimeField(read_only=True, required=False, label='created at')
    updated_at = fields.DateTimeField(read_only=True, required=False, label='updated at')
    klass = fields.Field(read_only=False, required=True, label='class')
    signal = fields.ChoiceField(read_only=False, choices=SIGNAL_CHOICES, required=True, label='signal')

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["put", "get", "patch", "delete"],
                "path": "/v1/instances/{instance_name}/triggers/{id}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/instances/{instance_name}/triggers/",
            }
        }


class Webhook(Model):
    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'run', 'name': 'run'},
    )

    codebox = fields.Field(read_only=False, required=True, label='codebox')
    slug = fields.SlugField(read_only=False, max_length=50, required=True, label='slug')
    links = fields.HyperlinkedField(read_only=True, required=False, links=LINKS)

    class Meta:
        endpoints = {
            "detail": {
                "methods": ["put", "get", "patch", "delete"],
                "path": "/v1/instances/{instance_name}/webhooks/{id}/",
            },
            "list": {
                "methods": ["post", "get"],
                "path": "/v1/instances/{instance_name}/webhooks/",
            },
            "run": {
                "methods": ["get"],
                "path": "/v1/instances/{instance_name}/webhooks/{id}/run/",
            }
        }
