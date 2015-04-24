import json
from threading import Thread

from requests import Timeout
from syncano import logger

from .base import Instance, Model, fields


class PollThread(Thread):
    def __init__(self, connection, endpoint, callback, error, *args, **kwargs):
        self.connection = connection
        self.endpoint = endpoint
        self.callback = callback
        self.error = error
        self.abort = False
        self.timeout = kwargs.pop('timeout', 60)
        self.last_id = kwargs.pop('last_id', None)
        self.room = kwargs.pop('room', None)
        super(PollThread, self).__init__(*args, **kwargs)

        logger.debug('PollThread: %s created.', self.getName())

    def request(self):
        kwargs = {
            'timeout': self.timeout,
            'params': {'last_id': self.last_id, 'room': self.room}
        }
        return self.connection.request('GET', self.endpoint, **kwargs)

    def run(self):
        while self.abort is False:
            try:
                response = self.request()
            except Timeout as e:
                logger.debug('<PollThread: %s> Timeout.', self.getName())
                if not self.callback(None):
                    self.stop()
            except Exception as e:
                logger.error('<PollThread: %s> Error "%s"', self.getName(), e)
                if self.error:
                    self.error(e)
                return
            else:
                logger.debug('<PollThread: %s> Message "%s"', self.getName(), response['id'])
                self.last_id = response['id']
                if not self.callback(Message(**response)):
                    self.stop()

    def stop(self):
        self.abort = True
        self.callback = None
        self.error = None


class Channel(Model):
    TYPE_CHOICES = (
        {'display_name': 'Default', 'value': 0},
        {'display_name': 'Separate rooms', 'value': 1},
    )

    PERMISSIONS_CHOICES = (
        {'display_name': 'none', 'value': 0},
        {'display_name': 'subscribe', 'value': 1},
        {'display_name': 'publish', 'value': 2},
    )

    name = fields.StringField(max_length=64, primary_key=True)
    type = fields.ChoiceField(choices=TYPE_CHOICES, required=False)
    group = fields.IntegerField(label='group id', required=False)
    group_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default=0)
    other_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default=0)
    custom_publish = fields.BooleanField(default=False)

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['put', 'get', 'patch', 'delete'],
                'path': '/channels/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/channels/',
            },
            'poll': {
                'methods': ['get'],
                'path': '/channels/{name}/poll/',
            },
            'publish': {
                'methods': ['post'],
                'path': '/channels/{name}/publish/',
            },
            'history': {
                'methods': ['get'],
                'path': '/channels/{name}/history/',
            },
        }

    def poll(self, room=None, last_id=None, callback=None, error=None):
        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('poll', properties)
        connection = self._get_connection()

        thread = PollThread(connection, endpoint, callback, error,
                            last_id=last_id, room=room, name='poll_%s' % self.name)
        thread.start()
        return thread.stop

    def publish(self, payload, room=None):
        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('publish', properties)
        connection = self._get_connection()
        request = {
            'data': {
                'payload': json.dumps(payload),
                'room': room,
            }
        }
        response = connection.request('POST', endpoint, **request)
        return Message(**response)


class Message(Model):
    ACTION_CHOICES = (
        {'display_name': 'custom', 'value': 0},
        {'display_name': 'create', 'value': 1},
        {'display_name': 'update', 'value': 2},
        {'display_name': 'delete', 'value': 3},
    )

    room = fields.StringField(max_length=50)
    action = fields.ChoiceField(choices=ACTION_CHOICES, read_only=True)
    author = fields.JSONField(required=False, read_only=True)
    metadata = fields.JSONField(required=False, read_only=True)
    payload = fields.JSONField()
    created_at = fields.DateTimeField()

    class Meta:
        parent = Channel
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/history/{pk}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/history/',
            },
        }
