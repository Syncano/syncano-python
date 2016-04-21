# -*- coding: utf-8 -*-
from syncano.exceptions import SyncanoRequestError
from syncano.models import APNSDevice, APNSMessage, GCMDevice, GCMMessage
from tests.integration_test import InstanceMixin, IntegrationTest


class PushNotificationTest(InstanceMixin, IntegrationTest):
    def test_gcm_device(self):
        device = GCMDevice(
            instance_name=self.instance.name,
            label='example label',
            registration_id=86152312314401555,
            device_id='10000000001',
        )
        self._test_device(device, GCMDevice.please)

    def test_apns_device(self):
        device = APNSDevice(
            instance_name=self.instance.name,
            label='example label',
            registration_id='4719084371920471208947120984731208947910827409128470912847120894',
            device_id='7189d7b9-4dea-4ecc-aa59-8cc61a20608a',
        )

        self._test_device(device, APNSDevice.please)

    def test_gcm_message(self):
        message = GCMMessage(
            instance_name=self.instance.name,
            content={
                'registration_ids': ['TESTIDREGISRATION', ],
                'data': {
                    'param1': 'test'
                }
            }
        )

        self._test_message(message, GCMMessage.please)

    def test_apns_message(self):
        message = APNSMessage(
            instance_name=self.instance.name,
            content={
                'registration_ids': ['TESTIDREGISRATION', ],
                'aps': {'alert': 'semo example label'}
            }
        )

        self._test_message(message, APNSMessage.please)

    def _test_device(self, device, manager):

        self.assertFalse(manager.all(instance_name=self.instance.name))

        device.save()

        self.assertEqual(len(list(manager.all(instance_name=self.instance.name,))), 1)

        # test get:
        device_ = manager.get(instance_name=self.instance.name, registration_id=device.registration_id)

        self.assertEqual(device_.label, device.label)
        self.assertEqual(device_.registration_id, device.registration_id)
        self.assertEqual(device_.device_id, device.device_id)

        # test update:
        new_label = 'totally new label'
        device.label = new_label
        device.save()

        device_ = manager.get(instance_name=self.instance.name, registration_id=device.registration_id)
        self.assertEqual(new_label, device_.label)

        device.delete()

        self.assertFalse(manager.all(instance_name=self.instance.name))

    def _test_message(self, message, manager):
        self.assertFalse(manager.all(instance_name=self.instance.name))

        with self.assertRaises(SyncanoRequestError):
            # unable to save because of lack of API key;
            message.save()
