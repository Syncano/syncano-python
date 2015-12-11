from __future__ import unicode_literals

import json

from syncano.exceptions import SyncanoValidationError

from . import fields
from .base import Model
from .instances import Instance
from .manager import CodeBoxManager, WebhookManager


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
        {'type': 'list', 'name': 'traces'},
    )
    RUNTIME_CHOICES = (
        {'display_name': 'nodejs', 'value': 'nodejs'},
        {'display_name': 'python', 'value': 'python'},
        {'display_name': 'ruby', 'value': 'ruby'},
        {'display_name': 'golang', 'value': 'golang'},
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
        from .traces import CodeBoxTrace

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
        {'type': 'detail', 'name': 'codebox'},
        {'type': 'list', 'name': 'traces'},
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


class Trigger(Model):
    """
    OO wrapper around triggers `endpoint <http://docs.syncano.com/v4.0/docs/triggers-list>`_.

    :ivar label: :class:`~syncano.models.fields.StringField`
    :ivar codebox: :class:`~syncano.models.fields.IntegerField`
    :ivar class_name: :class:`~syncano.models.fields.StringField`
    :ivar signal: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    """
    LINKS = (
        {'type': 'detail', 'name': 'self'},
        {'type': 'detail', 'name': 'codebox'},
        {'type': 'detail', 'name': 'class_name'},
        {'type': 'list', 'name': 'traces'},
    )
    SIGNAL_CHOICES = (
        {'display_name': 'post_update', 'value': 'post_update'},
        {'display_name': 'post_create', 'value': 'post_create'},
        {'display_name': 'post_delete', 'value': 'post_delete'},
    )

    label = fields.StringField(max_length=80)
    codebox = fields.IntegerField(label='codebox id')
    class_name = fields.StringField(label='class name', mapping='class')
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
        {'type': 'list', 'name': 'traces'},
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
            'reset': {
                'methods': ['post'],
                'path': '/webhooks/{name}/reset_link/',
            },
            'public': {
                'methods': ['get'],
                'path': '/webhooks/p/{public_link}/{name}/',
            }
        }

    def run(self, **payload):
        """
        Usage::

            >>> wh = Webhook.please.get('instance-name', 'webhook-name')
            >>> wh.run()
            >>> wh.run(variable_one=1, variable_two=2)
        """
        from .traces import WebhookTrace

        if self.is_new():
            raise SyncanoValidationError('Method allowed only on existing model.')

        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('run', properties)
        connection = self._get_connection(**payload)

        response = connection.request('POST', endpoint, **{'data': payload})
        if 'result' in response and 'stdout' in response['result']:
            response.update({'instance_name': self.instance_name,
                             'webhook_name': self.name})
            return WebhookTrace(**response)
        # if codebox is a custom one, return result 'as-it-is';
        return response

    def reset_link(self):
        """
        Usage::

            >>> wh = Webhook.please.get('instance-name', 'webhook-name')
            >>> wh.reset_link()
        """
        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('reset', properties)
        connection = self._get_connection()

        response = connection.request('POST', endpoint)
        self.public_link = response['public_link']
