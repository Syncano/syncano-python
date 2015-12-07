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
    user_id = fields.IntegerField(required=False)

    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        abstract = True

    def is_new(self):
        return self.created_at is None


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

    Note::

        another save on the same object will always fail (altering the Device data is currently not possible);

    Delete a Device:

        gcm_device.delete()

    Read a Device data:

        gcm_device = GCMDevice.please.get(registration_id=86152312314401554)

    """

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['delete', 'get'],
                'path': '/push_notifications/gcm/devices/{registration_id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/push_notifications/gcm/devices/',
            }
        }


class APNSDevice(DeviceBase, Model):
    """
    Model which handles the Apple Push Notification Server Device.
    CORE supports only Create, Delete and Read;

    Usage::

    Create
        apns_device = APNSDevice(
            label='example label',
            registration_id='4719084371920471208947120984731208947910827409128470912847120894',
            user_id=u.id,
            device_id='7189d7b9-4dea-4ecc-aa59-8cc61a20608a',
        )
        apns_device.save()

    Note::

        another save on the same object will always fail (altering the Device data is currently not possible);

        Also note the different format (from GCM) of registration_id required by APNS; the device_id have different
         format too.

    Read
        apns_device =
            APNSDevice.please.get(registration_id='4719084371920471208947120984731208947910827409128470912847120894')

    Delete
        apns_device.delete()

    """
    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['delete', 'get'],
                'path': '/push_notifications/apns/devices/{registration_id}/',
            },
            'list': {
                'methods': ['get'],
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

    Create


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

        The data parameter is passed as-it-is to the GCM server; Base checking is made on syncano CORE;
        For more details read the GCM documentation;

    Note::
        Every save after initial one will raise an error;

    Read
        gcm_message = GCMMessage.please.get(id=1)

    Debugging:
        gcm_message.status - on of the (scheduled, error, partially_delivered, delivered)
        gcm_message.result - a result from GCM server;

    Note::
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

    Create
        apns_message = APNSMessage(
            content={
                'registration_ids': [gcm_device.registration_id],
                'aps': {'alert': 'test alert'},
            }
        )

        apns_message.save()

        The 'aps' data is send 'as-it-is' to APNS, some validation is made on syncano CORE;
        For more details read the APNS documentation;

    Note::
        Every save after initial one will raise an error;

    Read
        apns_message = APNSMessage.please.get(id=1)

    Debugging
        apns_message.status - one of the following: scheduled, error, partially_delivered, delivered;
        apns_message.result - a result from APNS server;

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
