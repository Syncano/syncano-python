from threading import Thread

import six
from requests import Timeout
from syncano import logger

from . import fields
from .base import Model
from .instances import Instance


class PollThread(Thread):
    def __init__(self, connection, endpoint, callback, error=None, *args, **kwargs):
        self.connection = connection
        self.endpoint = endpoint
        self.callback = callback
        self.error = error
        self.abort = False
        self.timeout = kwargs.pop('timeout', None) or 60 * 5
        self.last_id = kwargs.pop('last_id', None)
        self.room = kwargs.pop('room', None)
        super(PollThread, self).__init__(*args, **kwargs)

        logger.debug('%s created.', self)

    def __str__(self):
        return '<PollThread: %s>' % self.getName()

    def __unicode__(self):
        return six.u(str(self))

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
                logger.debug('%s Timeout.', self)
                if not self.callback(None):
                    self.stop()

            except Exception as e:
                logger.error('%s Error "%s"', self, e)
                if self.error:
                    self.error(e)
                return
            else:
                logger.debug('%s Message "%s"', self, response['id'])
                self.last_id = response['id']
                if not self.callback(Message(**response)):
                    self.stop()

    def stop(self):
        self.abort = True
        self.callback = None
        self.error = None


class Channel(Model):
    """
    .. _long polling: http://en.wikipedia.org/wiki/Push_technology#Long_polling

    OO wrapper around channels `link http://docs.syncano.io/docs/realtime-communication`_.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar type: :class:`~syncano.models.fields.ChoiceField`
    :ivar group: :class:`~syncano.models.fields.IntegerField`
    :ivar group_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar other_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar custom_publish: :class:`~syncano.models.fields.BooleanField`

    .. note::
        **Channel** has two special methods called ``publish`` and ``poll``.
        First one will send message to the channel::

            >>> channel = Channel.please.get('instance-name', 'channel-name')
            >>> channel.publish({"x": 1})

        second one will create `long polling`_ connection which will listen for messages::

            >>> def callback(message=None):
            ...    print message
            ...    return True

            >>> channel = Channel.please.get('instance-name', 'channel-name')
            >>> channel.poll(callback=callback)
    """

    TYPE_CHOICES = (
        {'display_name': 'Default', 'value': 'default'},
        {'display_name': 'Separate rooms', 'value': 'separate_rooms'},
    )

    PERMISSIONS_CHOICES = (
        {'display_name': 'None', 'value': 'none'},
        {'display_name': 'Subscribe', 'value': 'subscribe'},
        {'display_name': 'Publish', 'value': 'publish'},
    )

    name = fields.StringField(max_length=64, primary_key=True)
    type = fields.ChoiceField(choices=TYPE_CHOICES, required=False, default='default')
    group = fields.IntegerField(label='group id', required=False)
    group_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    other_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    custom_publish = fields.BooleanField(default=False, required=False)
    links = fields.LinksField()

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

    def poll(self, room=None, last_id=None, callback=None, error=None, timeout=None):
        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('poll', properties)
        connection = self._get_connection()

        thread = PollThread(connection, endpoint, callback, error, timeout=timeout,
                            last_id=last_id, room=room, name='poll_%s' % self.name)
        thread.start()
        return thread.stop

    def publish(self, payload, room=None):
        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('publish', properties)
        connection = self._get_connection()
        request = {'data': Message(payload=payload, room=room).to_native()}
        response = connection.request('POST', endpoint, **request)
        return Message(**response)


class Message(Model):
    """
    OO wrapper around channel hisotry `link http://docs.syncano.io/docs/realtime-communication`_.

    :ivar room: :class:`~syncano.models.fields.StringField`
    :ivar action: :class:`~syncano.models.fields.ChoiceField`
    :ivar author: :class:`~syncano.models.fields.JSONField`
    :ivar metadata: :class:`~syncano.models.fields.JSONField`
    :ivar payload: :class:`~syncano.models.fields.JSONField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    """

    ACTION_CHOICES = (
        {'display_name': 'custom', 'value': 0},
        {'display_name': 'create', 'value': 1},
        {'display_name': 'update', 'value': 2},
        {'display_name': 'delete', 'value': 3},
    )

    room = fields.StringField(max_length=50, required=False)
    action = fields.ChoiceField(choices=ACTION_CHOICES, read_only=True)
    author = fields.JSONField(required=False, read_only=True)
    metadata = fields.JSONField(required=False, read_only=True)
    payload = fields.JSONField()
    created_at = fields.DateTimeField(required=False, read_only=True)

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
