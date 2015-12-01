# -*- coding: utf-8 -*-

from . import fields
from .base import Instance, Model


class GCMDevice(Model):
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

    def is_new(self):
        return self.created_at is None


class GCMMessage(Model):
    """
    Model which handles the Google Cloud Messaging Message.
    Only creating and reading is allowed.

    Usage::

    Create
        The content parameter is passed as-it-is to the GCM server; Base checking is made on syncano CORE;

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
    STATUS_CHOICES = (
        {'display_name': 'scheduled', 'value': 0},
        {'display_name': 'error', 'value': 1},
        {'display_name': 'partially_delivered', 'value': 2},
        {'display_name': 'delivered', 'value': 3},
    )

    status = fields.ChoiceField(choices=STATUS_CHOICES, read_only=True)
    content = fields.PushJSONField(default={})
    result = fields.JSONField(default={}, read_only=True)

    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

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
