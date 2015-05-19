import os
import unittest
from uuid import uuid4
from hashlib import md5

import syncano
from syncano.exceptions import SyncanoValueError


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

    @classmethod
    def generate_hash(cls):
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
        name = 'i%s' % self.generate_hash()[:10]
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
        name = 'i%s' % self.generate_hash()[:10]
        description = 'test'

        instance = self.model.please.create(name=name, description=description)
        instance.description = 'test'
        instance.save()

        instance2 = self.model.please.get(name=name)
        self.assertEqual(instance.description, instance2.description)

        instance.delete()

    def test_delete(self):
        name = 'i%s' % self.generate_hash()[:10]
        description = 'test'

        instance = self.model.please.create(name=name, description=description)
        instance.delete()

        with self.assertRaises(self.model.DoesNotExist):
            self.model.please.get(name=name)


class ClassIntegrationTest(IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(ClassIntegrationTest, cls).setUpClass()

        cls.instance = cls.connection.Instance.please.create(
            name='i%s' % cls.generate_hash()[:10],
            description='test',
        )
        cls.model = cls.connection.Class

    @classmethod
    def tearDownClass(cls):
        cls.instance.delete()
        super(ClassIntegrationTest, cls).tearDownClass()

    def test_instance_name_is_required(self):
        with self.assertRaises(SyncanoValueError):
            list(self.model.please.all())

        with self.assertRaises(SyncanoValueError):
            self.model.please.create()

    def test_list(self):
        classes = self.model.please.all(instance_name=self.instance.name)
        self.assertEqual(len(list(classes)), 1)

        cls = self.model.please.create(instance_name=self.instance.name, name='test',
                                       schema=[{'type': 'string', 'name': 'test'}])
        classes = self.model.please.all(instance_name=self.instance.name)
        self.assertEqual(len(list(classes)), 2)

        cls.delete()

    def test_create(self):
        cls_one = self.model.please.create(
            instance_name=self.instance.name,
            name='c%s' % self.generate_hash()[:10],
            schema=[
                {'type': 'string', 'name': 'string_test'},
                {'type': 'text', 'name': 'text_test'},
                {'type': 'integer', 'name': 'integer_test', 'order_index': True, 'filter_index': True},
                {'type': 'float', 'name': 'float_test'},
                {'type': 'boolean', 'name': 'boolean_test'},
                {'type': 'datetime', 'name': 'datetime_test'},
                {'type': 'file', 'name': 'file_test'},
            ]
        )

        cls_two = self.model.please.create(
            instance_name=self.instance.name,
            name='c%s' % self.generate_hash()[:10],
            schema=[
                {'type': 'string', 'name': 'string_test'},
                {'type': 'text', 'name': 'text_test'},
                {'type': 'integer', 'name': 'integer_test'},
                {'type': 'float', 'name': 'float_test'},
                {'type': 'boolean', 'name': 'boolean_test'},
                {'type': 'datetime', 'name': 'datetime_test'},
                {'type': 'file', 'name': 'file_test'},
                {'type': 'reference', 'name': 'reference_test',
                 'order_index': True, 'filter_index': True, 'target': cls_one.name},
            ]
        )

        cls_one.delete()
        cls_two.delete()

    def test_update(self):
        cls = self.model.please.create(
            instance_name=self.instance.name,
            name='c%s' % self.generate_hash()[:10],
            schema=[
                {'type': 'string', 'name': 'string_test'},
                {'type': 'text', 'name': 'text_test'},
                {'type': 'integer', 'name': 'integer_test', 'order_index': True, 'filter_index': True},
                {'type': 'float', 'name': 'float_test'},
                {'type': 'boolean', 'name': 'boolean_test'},
                {'type': 'datetime', 'name': 'datetime_test'},
                {'type': 'file', 'name': 'file_test'},
            ]
        )
        cls.description = 'dummy'
        cls.save()

        cls2 = self.model.please.get(instance_name=self.instance.name, name=cls.name)
        self.assertEqual(cls.description, cls2.description)

        cls.delete()


class ObjectIntegrationTest(IntegrationTest):
    pass
