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
            label='dummy label',
            registration_id=86152312314401555,
            user_id=u.id,
            device_id='32132132132131',
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
                'methods': ['delete', 'post', 'get'],
                'path': '/push_notifications/gcm/devices/{registration_id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/push_notifications/gcm/devices/',
            }
        }

    def is_new(self):
        if self.created_at is None:
            return True
        return False
