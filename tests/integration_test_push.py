# -*- coding: utf-8 -*-
import uuid

from syncano.exceptions import SyncanoRequestError
from syncano.models import APNSConfig, APNSDevice, APNSMessage, GCMConfig, GCMDevice, GCMMessage
from tests.integration_test import InstanceMixin, IntegrationTest


class PushIntegrationTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(PushIntegrationTest, cls).setUpClass()

        cls.gcm_config = GCMConfig(
            development_api_key=uuid.uuid4().hex,
            instance_name=cls.instance.name
        )
        cls.gcm_config.save()

        with open('tests/certificates/ApplePushDevelopment.p12', 'rb') as cert:
            cls.apns_config = APNSConfig(
                development_certificate=cert,
                development_certificate_name='test',
                development_bundle_identifier='test1234',
                instance_name=cls.instance.name
            )
            cls.apns_config.save()

        cls.environment = 'development'
        cls.gcm_device = GCMDevice(
            instance_name=cls.instance.name,
            label='example label',
            registration_id=86152312314401555,
            device_id='10000000001',
        )
        cls.gcm_device.save()

        cls.apns_device = APNSDevice(
            instance_name=cls.instance.name,
            label='example label',
            registration_id='4719084371920471208947120984731208947910827409128470912847120894',
            device_id='7189d7b9-4dea-4ecc-aa59-8cc61a20608a',
        )
        cls.apns_device.save()


class PushNotificationTest(PushIntegrationTest):

    def test_gcm_config_update(self):
        gcm_config = GCMConfig.please.get()
        new_key = uuid.uuid4().hex
        gcm_config.development_api_key = new_key
        gcm_config.save()

        gcm_config_ = GCMConfig.please.get()
        self.assertEqual(gcm_config_.development_api_key, new_key)

    def test_apns_config_update(self):
        apns_config = APNSConfig.please.get()
        new_cert_name = 'new cert name'
        apns_config.development_certificate_name = new_cert_name
        apns_config.save()

        apns_config_ = APNSConfig.please.get()
        self.assertEqual(apns_config_.development_certificate_name, new_cert_name)

    def test_gcm_device(self):
        device = GCMDevice(
            instance_name=self.instance.name,
            label='example label',
            registration_id=86152312314401666,
            device_id='10000000001',
        )
        self._test_device(device, GCMDevice.please)

    def test_apns_device(self):
        device = APNSDevice(
            instance_name=self.instance.name,
            label='example label',
            registration_id='4719084371920471208947120984731208947910827409128470912847120222',
            device_id='7189d7b9-4dea-4ecc-aa59-8cc61a20608a',
        )

        self._test_device(device, APNSDevice.please)

    def test_send_message_gcm(self):

        self.assertEqual(0, len(list(GCMMessage.please.all())))

        self.gcm_device.send_message(content={'environment': self.environment, 'data': {'c': 'more_c'}})

        self.assertEqual(1, len(list(GCMMessage.please.all())))

    def test_send_message_apns(self):
        self.assertEqual(0, len(list(APNSMessage.please.all())))

        self.apns_device.send_message(content={'environment': 'development', 'aps': {'alert': 'alert test'}})

        self.assertEqual(1, len(list(APNSMessage.please.all())))

    def test_gcm_message(self):
        message = GCMMessage(
            instance_name=self.instance.name,
            content={
                'registration_ids': ['TESTIDREGISRATION', ],
                'environment': 'production',
                'data': {
                    'param1': 'test'
                }
            }
        )

        self._test_message(message, GCMMessage.please)  # we want this to fail; no productions keys;

    def test_apns_message(self):
        message = APNSMessage(
            instance_name=self.instance.name,
            content={
                'registration_ids': ['TESTIDREGISRATION', ],
                'environment': 'production',
                'aps': {'alert': 'semo example label'}
            }
        )

        self._test_message(message, APNSMessage.please)  # we want this to fail; no productions certs;

    def _test_device(self, device, manager):

        device.save()

        self.assertEqual(len(list(manager.all(instance_name=self.instance.name,))), 2)

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

    def _test_message(self, message, manager):
        self.assertFalse(manager.all(instance_name=self.instance.name))

        with self.assertRaises(SyncanoRequestError):
            # unable to save because of lack of API key;
            message.save()
