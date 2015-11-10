import os
import unittest
from datetime import datetime
from hashlib import md5
from time import sleep
from uuid import uuid4

import syncano
from syncano.exceptions import SyncanoRequestError, SyncanoValueError
from syncano.models import Class, CodeBox, Instance, Object, Webhook


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
        return md5('%s%s' % (uuid4(), datetime.now())).hexdigest()


class InstanceMixin(object):

    @classmethod
    def setUpClass(cls):
        super(InstanceMixin, cls).setUpClass()

        cls.instance = cls.connection.Instance.please.create(
            name='i%s' % cls.generate_hash()[:10],
            description='IntegrationTest %s' % datetime.now(),
        )

    @classmethod
    def tearDownClass(cls):
        cls.instance.delete()
        super(InstanceMixin, cls).tearDownClass()


class InstanceIntegrationTest(IntegrationTest):
    model = Instance

    @classmethod
    def tearDownClass(cls):
        for i in cls.connection.Instance.please.all():
            i.delete()
        cls.connection = None

    def test_list(self):
        instances = self.model.please.all()
        self.assertTrue(len(list(instances)) >= 0)

    def test_create(self):
        name = 'i%s' % self.generate_hash()[:10]
        description = 'IntegrationTest'

        self.assertEqual(len(self.model.please.list()), 1)  # auto create first instance;

        instance = self.model.please.create(name=name, description=description)
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.name, name)
        self.assertEqual(instance.description, description)

        self.assertTrue(bool(self.model.please.list()))
        instance.delete()

        instance = self.model(name=name, description=description)
        instance.save()
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.name, name)
        self.assertEqual(instance.description, description)
        instance.delete()

    def test_update(self):
        name = 'i%s' % self.generate_hash()[:10]
        description = 'IntegrationTest'

        instance = self.model.please.create(name=name, description=description)
        instance.description = 'NotIntegrationTest'
        instance.save()

        instance2 = self.model.please.get(name=name)
        self.assertEqual(instance.description, instance2.description)

        instance.delete()

    def test_delete(self):
        name = 'i%s' % self.generate_hash()[:10]
        description = 'IntegrationTest'

        instance = self.model.please.create(name=name, description=description)
        instance.delete()

        with self.assertRaises(self.model.DoesNotExist):
            self.model.please.get(name=name)


class ClassIntegrationTest(InstanceMixin, IntegrationTest):
    model = Class

    def test_instance_name_is_required(self):
        with self.assertRaises(SyncanoValueError):
            list(self.model.please.all())

        with self.assertRaises(SyncanoValueError):
            self.model.please.create()

    def test_list(self):
        classes = self.model.please.all(instance_name=self.instance.name)
        self.assertTrue(len(list(classes)) >= 0)

        cls = self.model.please.create(instance_name=self.instance.name,
                                       name='IntegrationTest%s' % self.generate_hash()[:10],
                                       schema=[{'type': 'string', 'name': 'test'}])
        classes = self.model.please.all(instance_name=self.instance.name)
        self.assertTrue(len(list(classes)) >= 1)

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

        for i in xrange(3):
            try:
                cls.save()
            except SyncanoRequestError as e:
                if i == 2:
                    raise

                if e.status_code == 400 and e.reason.startswith('Cannot modify class.'):
                    sleep(2)

        cls2 = self.model.please.get(instance_name=self.instance.name, name=cls.name)
        self.assertEqual(cls.description, cls2.description)

        cls.delete()


class ObjectIntegrationTest(InstanceMixin, IntegrationTest):
    model = Object

    @classmethod
    def setUpClass(cls):
        super(ObjectIntegrationTest, cls).setUpClass()

        cls.author = cls.connection.Class.please.create(
            instance_name=cls.instance.name,
            name='author_%s' % cls.generate_hash()[:10],
            schema=[
                {'type': 'string', 'name': 'first_name', 'order_index': True, 'filter_index': True},
                {'type': 'string', 'name': 'last_name', 'order_index': True, 'filter_index': True},
            ]
        )

        cls.book = cls.connection.Class.please.create(
            instance_name=cls.instance.name,
            name='book_%s' % cls.generate_hash()[:10],
            schema=[
                {'type': 'string', 'name': 'name'},
                {'type': 'text', 'name': 'description'},
                {'type': 'integer', 'name': 'quantity'},
                {'type': 'float', 'name': 'cost'},
                {'type': 'boolean', 'name': 'available'},
                {'type': 'datetime', 'name': 'published_at'},
                {'type': 'file', 'name': 'cover'},
                {'type': 'reference', 'name': 'author',
                 'order_index': True, 'filter_index': True, 'target': cls.author.name},
            ]
        )

    @classmethod
    def tearDownClass(cls):
        cls.book.delete()
        cls.author.delete()
        super(ObjectIntegrationTest, cls).tearDownClass()

    def test_required_fields(self):
        with self.assertRaises(SyncanoValueError):
            list(self.model.please.all())

        with self.assertRaises(SyncanoValueError):
            list(self.model.please.all(instance_name=self.instance.name))

    def test_list(self):
        objects = self.model.please.all(self.instance.name, self.author.name)
        self.assertTrue(len(list(objects)) >= 0)

        objects = self.model.please.all(self.instance.name, self.book.name)
        self.assertTrue(len(list(objects)) >= 0)

    def test_create(self):
        author = self.model.please.create(
            instance_name=self.instance.name, class_name=self.author.name,
            first_name='john', last_name='doe')

        book = self.model.please.create(
            instance_name=self.instance.name, class_name=self.book.name,
            name='test', description='test', quantity=10, cost=10.5,
            published_at=datetime.now(), author=author, available=True)

        book.delete()
        author.delete()

    def test_update(self):
        author = self.model.please.create(
            instance_name=self.instance.name, class_name=self.author.name,
            first_name='john', last_name='doe')

        author.first_name = 'not john'
        author.last_name = 'not doe'
        author.save()

        author2 = self.model.please.get(author.instance_name, author.class_name, author.pk)
        self.assertEqual(author.first_name, author2.first_name)
        self.assertEqual(author.last_name, author2.last_name)

        author.delete()


class CodeboxIntegrationTest(InstanceMixin, IntegrationTest):
    model = CodeBox

    @classmethod
    def tearDownClass(cls):
        for cb in cls.instance.codeboxes.all():
            cb.delete()
        super(CodeboxIntegrationTest, cls).tearDownClass()

    def test_required_fields(self):
        with self.assertRaises(SyncanoValueError):
            list(self.model.please.all())

    def test_list(self):
        codeboxes = self.model.please.all(self.instance.name)
        self.assertTrue(len(list(codeboxes)) >= 0)

    def test_create(self):
        codebox = self.model.please.create(
            instance_name=self.instance.name,
            label='cb%s' % self.generate_hash()[:10],
            runtime_name='python',
            source='print "IntegrationTest"'
        )

        codebox.delete()

    def test_update(self):
        codebox = self.model.please.create(
            instance_name=self.instance.name,
            label='cb%s' % self.generate_hash()[:10],
            runtime_name='python',
            source='print "IntegrationTest"'
        )

        codebox.source = 'print "NotIntegrationTest"'
        codebox.save()

        codebox2 = self.model.please.get(self.instance.name, codebox.pk)
        self.assertEqual(codebox.source, codebox2.source)

        codebox.delete()

    def test_source_run(self):
        codebox = self.model.please.create(
            instance_name=self.instance.name,
            label='cb%s' % self.generate_hash()[:10],
            runtime_name='python',
            source='print "IntegrationTest"'
        )

        trace = codebox.run()
        while trace.status == 'pending':
            sleep(1)
            trace.reload()

        self.assertEquals(trace.status, 'success')
        self.assertEquals(trace.result, u'{u\'stderr\': u\'\', u\'stdout\': u\'IntegrationTest\'}')

        codebox.delete()


class WebhookIntegrationTest(InstanceMixin, IntegrationTest):
    model = Webhook

    @classmethod
    def setUpClass(cls):
        super(WebhookIntegrationTest, cls).setUpClass()

        cls.codebox = CodeBox.please.create(
            instance_name=cls.instance.name,
            label='cb%s' % cls.generate_hash()[:10],
            runtime_name='python',
            source='print "IntegrationTest"'
        )

    @classmethod
    def tearDownClass(cls):
        cls.codebox.delete()
        super(WebhookIntegrationTest, cls).tearDownClass()

    def test_required_fields(self):
        with self.assertRaises(SyncanoValueError):
            list(self.model.please.all())

    def test_list(self):
        webhooks = self.model.please.all(self.instance.name)
        self.assertTrue(len(list(webhooks)) >= 0)

    def test_create(self):
        webhook = self.model.please.create(
            instance_name=self.instance.name,
            codebox=self.codebox.id,
            name='wh%s' % self.generate_hash()[:10],
        )

        webhook.delete()

    def test_codebox_run(self):
        webhook = self.model.please.create(
            instance_name=self.instance.name,
            codebox=self.codebox.id,
            name='wh%s' % self.generate_hash()[:10],
        )

        trace = webhook.run()
        self.assertEquals(trace.status, 'success')
        self.assertEquals(trace.result, u'{u\'stderr\': u\'\', u\'stdout\': u\'IntegrationTest\'}')
        webhook.delete()
