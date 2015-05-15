import os
import unittest
from uuid import uuid4
from hashlib import md5

import syncano


class IntegrationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.API_KEY = os.getenv('INTEGRATION_API_KEY')
        cls.API_EMAIL = os.getenv('INTEGRATION_API_EMAIL')
        cls.API_PASSWORD = os.getenv('INTEGRATION_API_PASSWORD')
        cls.API_ROOT = os.getenv('INTEGRATION_API_ROOT')

        cls.connection = syncano.connect(
            host=cls.API_ROOT,
            email=cls.API_EMAIL,
            password=cls.API_PASSWORD,
            api_key=cls.API_KEY
        )

    @classmethod
    def tearDownClass(cls):
        cls.connection = None

    def generate_hash(self):
        return md5(str(uuid4())).hexdigest()


class InstanceIntegrationTest(IntegrationTest):

    def setUp(self):
        self.model = self.connection.Instance

    @classmethod
    def tearDownClass(cls):
        for i in cls.connection.Instance.please.all():
            i.delete()
        cls.connection = None

    def test_list(self):
        instances = self.model.please.all()
        self.assertEqual(len(list(instances)), 0)

    def test_create(self):
        name = 'a%s' % self.generate_hash()[:10]
        description = 'test'

        instance = self.model.please.create(name=name, description=description)
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.name, name)
        self.assertEqual(instance.description, description)
        instance.delete()

        instance = self.model(name=name, description=description)
        instance.save()
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.name, name)
        self.assertEqual(instance.description, description)
        instance.delete()

    def test_update(self):
        name = 'a%s' % self.generate_hash()[:10]
        description = 'test'

        instance = self.model.please.create(name=name, description=description)
        instance.description = 'test'
        instance.save()

        instance2 = self.model.please.get(name=name)
        self.assertEqual(instance.description, instance2.description)

        instance.delete()

    def test_delete(self):
        name = 'a%s' % self.generate_hash()[:10]
        description = 'test'

        instance = self.model.please.create(name=name, description=description)
        instance.delete()

        with self.assertRaises(self.model.DoesNotExist):
            self.model.please.get(name=name)


class ClassIntegrationTest(IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(ClassIntegrationTest, cls).setUpClass()
