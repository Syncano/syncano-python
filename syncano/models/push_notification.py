# -*- coding: utf-8 -*-

from . import fields
from .base import Instance, Model


class DeviceBase(object):
    """
    Base abstract class for GCM and APNS Devices;
    """
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    registration_id = fields.StringField(max_length=512, unique=True, primary_key=True)
    device_id = fields.StringField(required=False)
    is_active = fields.BooleanField(default=True)
    label = fields.StringField(max_length=80)
    user = fields.IntegerField(required=False)

    links = fields.LinksField()
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        abstract = True

    def send_message(self, content):
        """
        A method which allows to send message directly to the device;
        :param contet: Message content structure - object like;
        :return:
        """
        send_message_path = self.links.send_message
        data = {
            'content': content
        }
        connection = self._get_connection()
        response = connection.request('POST', send_message_path, data=data)
        self.to_python(response)
        return self


class GCMDevice(DeviceBase, Model):
    """
    Model which handles the Google Cloud Message Device.
    CORE supports only Create, Delete and Read;

    Usage::

        Create a new Device:
        gcm_device = GCMDevice(
            label='example label',
            registration_id=86152312314401555,
            user_id=u.id,
            device_id='10000000001',
        )

        gcm_device.save()

        Read:
        gcm_device = GCMDevice.please.get(registration_id=86152312314401554)

        Delete:
        gcm_device.delete()

        Update:
        gcm_device.label = 'some new label'
        gcm_device.save()

    """

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['delete', 'get', 'put', 'patch'],
                'path': '/push_notifications/gcm/devices/{registration_id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/push_notifications/gcm/devices/',
            }
        }


class APNSDevice(DeviceBase, Model):
    """
    Model which handles the Apple Push Notification Server Device.
    CORE supports only Create, Delete and Read;

    Usage::

        Create a new Device:
        apns_device = APNSDevice(
            label='example label',
            registration_id='4719084371920471208947120984731208947910827409128470912847120894',
            user_id=u.id,
            device_id='7189d7b9-4dea-4ecc-aa59-8cc61a20608a',
        )
        apns_device.save()

        Read:
        apns_device =
            APNSDevice.please.get(registration_id='4719084371920471208947120984731208947910827409128470912847120894')

        Delete:
        apns_device.delete()

        Update:
        apns_device.label = 'some new label'
        apns_device.save()

    .. note::

        Also note the different format (from GCM) of registration_id required by APNS; the device_id have different
        format too.

    """
    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['delete', 'get', 'put', 'patch'],
                'path': '/push_notifications/apns/devices/{registration_id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/push_notifications/apns/devices/',
            }
        }


class MessageBase(object):
    """
    Base abstract class for GCM and APNS Messages;
    """

    status = fields.StringField(read_only=True)
    content = fields.PushJSONField(default={})
    result = fields.JSONField(default={}, read_only=True)

    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        abstract = True


class GCMMessage(MessageBase, Model):
    """
    Model which handles the Google Cloud Messaging Message.
    Only creating and reading is allowed.

    Usage::

        Create a new Message:

        message = GCMMessage(
            content={
                'registration_ids': [gcm_device.registration_id],  # maximum 1000 elements;
                'data': {
                    'example_data_one': 1,
                    'example_data_two': 2,
                }
            }
        )
        message.save()


        Read:

        gcm_message = GCMMessage.please.get(id=1)

        Debugging:

        gcm_message.status - on of the (scheduled, error, partially_delivered, delivered)
        gcm_message.result - a result from GCM server;


    The data parameter is passed as-it-is to the GCM server; Base checking is made on syncano CORE;
    For more details read the GCM documentation;

    .. note::
        Every save after initial one will raise an error;

    .. note::
        The altering of existing Message is not possible. It also not possible to delete message.

    """

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['delete', 'get'],
                'path': '/push_notifications/gcm/messages/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/push_notifications/gcm/messages/',
            }
        }


class APNSMessage(MessageBase, Model):
    """
    Model which handles the Apple Push Notification Server Message.
    Only creating and reading is allowed.

    Usage::

        Create new Message:
        apns_message = APNSMessage(
            content={
                'registration_ids': [gcm_device.registration_id],
                'aps': {'alert': 'test alert'},
            }
        )

        apns_message.save()

        Read:

        apns_message = APNSMessage.please.get(id=1)

        Debugging:

        apns_message.status - one of the following: scheduled, error, partially_delivered, delivered;
        apns_message.result - a result from APNS server;

    The 'aps' data is send 'as-it-is' to APNS, some validation is made on syncano CORE;
    For more details read the APNS documentation;

    .. note::
        Every save after initial one will raise an error;

    """
    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['delete', 'get'],
                'path': '/push_notifications/apns/messages/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/push_notifications/apns/messages/',
            }
        }


class GCMConfig(Model):
    """
    A model which stores information with GCM Push keys;

    Usage::

        Add (modify) new keys:
        gcm_config = GCMConfig(production_api_key='ccc', development_api_key='ddd')
        gcm_config.save()

        or:
        gcm_config = GCMConfig().please.get()
        gcm_config.production_api_key = 'ccc'
        gcm_config.development_api_key = 'ddd'
        gcm_config.save()

    """
    production_api_key = fields.StringField(required=False)
    development_api_key = fields.StringField(required=False)

    def is_new(self):
        return False  # this is predefined - never will be new

    class Meta:
        parent = Instance
        endpoints = {
            'list': {
                'methods': ['get', 'put'],
                'path': '/push_notifications/gcm/config/',
            },
            'detail': {
                'methods': ['get', 'put'],
                'path': '/push_notifications/gcm/config/',
            },
        }


class APNSConfig(Model):
    """
    A model which stores information with APNS Push certificates;

    Usage::

        Add (modify) new keys:
        cert_file = open('cert_file.p12', 'rb')
        apns_config = APNSConfig(development_certificate=cert_file)
        apns_config.save()
        cert_file.close()

    """
    production_certificate_name = fields.StringField(required=False)
    production_certificate = fields.FileField(required=False)
    production_bundle_identifier = fields.StringField(required=False)
    production_expiration_date = fields.DateField(read_only=True)
    development_certificate_name = fields.StringField(required=False)
    development_certificate = fields.FileField(required=False)
    development_bundle_identifier = fields.StringField(required=False)
    development_expiration_date = fields.DateField(read_only=True)

    def is_new(self):
        return False  # this is predefined - never will be new

    class Meta:
        parent = Instance
        endpoints = {
            'list': {
                'methods': ['get', 'put'],
                'path': '/push_notifications/apns/config/',
            },
            'detail': {
                'methods': ['get', 'put'],
                'path': '/push_notifications/apns/config/',
            },
        }
