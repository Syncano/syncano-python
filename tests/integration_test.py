import os
import unittest
from datetime import datetime
from hashlib import md5
from time import sleep
from uuid import uuid4

import syncano
from syncano.exceptions import SyncanoRequestError, SyncanoValueError
from syncano.models import ApiKey, Class, DataEndpoint, Instance, Model, Object, Script, ScriptEndpoint, registry


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
        hash_feed = '{}{}'.format(uuid4(), datetime.now())
        return md5(hash_feed.encode('ascii')).hexdigest()


class InstanceMixin(object):

    @classmethod
    def setUpClass(cls):
        super(InstanceMixin, cls).setUpClass()

        cls.instance = cls.connection.Instance.please.create(
            name='testpythonlib%s' % cls.generate_hash()[:10],
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

    def test_rename(self):
        name = 'i%s' % self.generate_hash()[:10]
        new_name = 'icy-snow-jon-von-doe-312'

        instance = self.model.please.create(name=name, description='rest_rename')
        instance = instance.rename(new_name=new_name)

        self.assertEqual(instance.name, new_name)


class ClassIntegrationTest(InstanceMixin, IntegrationTest):
    model = Class

    def test_instance_name_is_required(self):
        registry.clear_used_instance()
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

        for i in range(3):
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
                {'type': 'array', 'name': 'array'},
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

        book_direct = Object(class_name=self.book.name, quantity=15, cost=7.5)
        book_direct.save()

        book.delete()
        book_direct.delete()
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

    def test_count_and_with_count(self):
        author_one = self.model.please.create(
            instance_name=self.instance.name, class_name=self.author.name,
            first_name='john1', last_name='doe1')

        author_two = self.model.please.create(
            instance_name=self.instance.name, class_name=self.author.name,
            first_name='john2', last_name='doe2')

        # just created two authors

        count = Object.please.list(instance_name=self.instance.name, class_name=self.author.name).count()
        self.assertEqual(count, 2)

        objects, count = Object.please.list(instance_name=self.instance.name,
                                            class_name=self.author.name).with_count()

        self.assertEqual(count, 2)
        for o in objects:
            self.assertTrue(isinstance(o, Model))

        author_one.delete()
        author_two.delete()

    def test_increment_and_decrement_on_integer(self):
        author = self.model.please.create(
            instance_name=self.instance.name, class_name=self.author.name,
            first_name='john', last_name='doe')

        book = self.model.please.create(
            instance_name=self.instance.name, class_name=self.book.name,
            name='test', description='test', quantity=10, cost=10.5,
            published_at=datetime.now(), author=author, available=True)

        incremented_book = Object.please.increment(
            'quantity',
            5,
            id=book.id,
            class_name=self.book.name,
        )

        self.assertEqual(incremented_book.quantity, 15)

        decremented_book = Object.please.decrement(
            'quantity',
            7,
            id=book.id,
            class_name=self.book.name,
        )

        self.assertEqual(decremented_book.quantity, 8)

    def test_increment_and_decrement_on_float(self):
        author = self.model.please.create(
            instance_name=self.instance.name, class_name=self.author.name,
            first_name='john', last_name='doe')

        book = self.model.please.create(
            instance_name=self.instance.name, class_name=self.book.name,
            name='test', description='test', quantity=10, cost=10.5,
            published_at=datetime.now(), author=author, available=True)

        incremented_book = Object.please.increment(
            'cost',
            5.5,
            id=book.id,
            class_name=self.book.name,
        )

        self.assertEqual(incremented_book.cost, 16)

        decremented_book = Object.please.decrement(
            'cost',
            7.6,
            id=book.id,
            class_name=self.book.name,
        )

        self.assertEqual(decremented_book.cost, 8.4)

    def test_add_array(self):
        book = self.model.please.create(
            instance_name=self.instance.name, class_name=self.book.name,
            name='test', description='test', quantity=10, cost=10.5,
            published_at=datetime.now(), available=True, array=[10])

        book = Object.please.add(
            'array',
            [11],
            class_name=self.book.name,
            id=book.id
        )

        self.assertEqual(book.array, [10, 11])

    def test_remove_array(self):
        book = self.model.please.create(
            instance_name=self.instance.name, class_name=self.book.name,
            name='test', description='test', quantity=10, cost=10.5,
            published_at=datetime.now(), available=True, array=[10])

        book = Object.please.remove(
            'array',
            [10],
            class_name=self.book.name,
            id=book.id
        )

        self.assertEqual(book.array, [])

    def test_addunique_array(self):
        book = self.model.please.create(
            instance_name=self.instance.name, class_name=self.book.name,
            name='test', description='test', quantity=10, cost=10.5,
            published_at=datetime.now(), available=True, array=[10])

        book = Object.please.add_unique(
            'array',
            [10],
            class_name=self.book.name,
            id=book.id
        )

        self.assertEqual(book.array, [10])

        book = Object.please.add_unique(
            'array',
            [11],
            class_name=self.book.name,
            id=book.id
        )

        self.assertEqual(book.array, [10, 11])


class ScriptIntegrationTest(InstanceMixin, IntegrationTest):
    model = Script

    @classmethod
    def tearDownClass(cls):
        for cb in cls.instance.scripts.all():
            cb.delete()
        super(ScriptIntegrationTest, cls).tearDownClass()

    def test_required_fields(self):
        with self.assertRaises(SyncanoValueError):
            registry.clear_used_instance()
            list(self.model.please.all())

    def test_list(self):
        scripts = self.model.please.all(self.instance.name)
        self.assertTrue(len(list(scripts)) >= 0)

    def test_create(self):
        script = self.model.please.create(
            instance_name=self.instance.name,
            label='cb%s' % self.generate_hash()[:10],
            runtime_name='python',
            source='print "IntegrationTest"'
        )

        script.delete()

    def test_update(self):
        script = self.model.please.create(
            instance_name=self.instance.name,
            label='cb%s' % self.generate_hash()[:10],
            runtime_name='python',
            source='print "IntegrationTest"'
        )

        script.source = 'print "NotIntegrationTest"'
        script.save()

        script2 = self.model.please.get(self.instance.name, script.pk)
        self.assertEqual(script.source, script2.source)

        script.delete()

    def test_source_run(self):
        script = self.model.please.create(
            instance_name=self.instance.name,
            label='cb%s' % self.generate_hash()[:10],
            runtime_name='python',
            source='print "IntegrationTest"'
        )

        trace = script.run()
        while trace.status == 'pending':
            sleep(1)
            trace.reload()

        self.assertEqual(trace.status, 'success')
        self.assertDictEqual(trace.result, {'stderr': '', 'stdout': 'IntegrationTest'})

        script.delete()

    def test_custom_response_run(self):
        script = self.model.please.create(
            instance_name=self.instance.name,
            label='cb%s' % self.generate_hash()[:10],
            runtime_name='python',
            source="""
set_response(HttpResponse(status_code=200, content='{"one": 1}', content_type='application/json'))"""
        )

        trace = script.run()
        while trace.status == 'pending':
            sleep(1)
            trace.reload()

        self.assertEqual(trace.status, 'success')
        self.assertDictEqual(trace.content, {'one': 1})
        self.assertEqual(trace.content_type, 'application/json')
        self.assertEqual(trace.status_code, 200)

        script.delete()


class ScriptEndpointIntegrationTest(InstanceMixin, IntegrationTest):
    model = ScriptEndpoint

    @classmethod
    def setUpClass(cls):
        super(ScriptEndpointIntegrationTest, cls).setUpClass()

        cls.script = Script.please.create(
            instance_name=cls.instance.name,
            label='cb%s' % cls.generate_hash()[:10],
            runtime_name='python',
            source='print "IntegrationTest"'
        )

        cls.custom_script = Script.please.create(
            instance_name=cls.instance.name,
            label='cb%s' % cls.generate_hash()[:10],
            runtime_name='python',
            source="""
set_response(HttpResponse(status_code=200, content='{"one": 1}', content_type='application/json'))"""
        )

    @classmethod
    def tearDownClass(cls):
        cls.script.delete()
        super(ScriptEndpointIntegrationTest, cls).tearDownClass()

    def test_required_fields(self):
        with self.assertRaises(SyncanoValueError):
            registry.clear_used_instance()
            list(self.model.please.all())

    def test_list(self):
        script_endpoints = self.model.please.all(self.instance.name)
        self.assertTrue(len(list(script_endpoints)) >= 0)

    def test_create(self):
        script_endpoint = self.model.please.create(
            instance_name=self.instance.name,
            script=self.script,
            name='wh%s' % self.generate_hash()[:10],
        )

        script_endpoint.delete()

    def test_script_run(self):
        script_endpoint = self.model.please.create(
            instance_name=self.instance.name,
            script=self.script,
            name='wh%s' % self.generate_hash()[:10],
        )

        trace = script_endpoint.run()
        self.assertEqual(trace.status, 'success')
        self.assertDictEqual(trace.result, {'stderr': '', 'stdout': 'IntegrationTest'})
        script_endpoint.delete()

    def test_custom_script_run(self):
        script_endpoint = self.model.please.create(
            instance_name=self.instance.name,
            script=self.custom_script,
            name='wh%s' % self.generate_hash()[:10],
        )

        trace = script_endpoint.run()
        self.assertDictEqual(trace, {'one': 1})
        script_endpoint.delete()


class ApiKeyIntegrationTest(InstanceMixin, IntegrationTest):
    model = ApiKey

    def test_api_key_flags(self):
        api_key = self.model.please.create(
            allow_user_create=True,
            ignore_acl=True,
            allow_anonymous_read=True,
            instance_name=self.instance.name,
        )

        reloaded_api_key = self.model.please.get(id=api_key.id, instance_name=self.instance.name)

        self.assertTrue(reloaded_api_key.allow_user_create, True)
        self.assertTrue(reloaded_api_key.ignore_acl, True)
        self.assertTrue(reloaded_api_key.allow_anonymous_read, True)


class DataEndpointIntegrationTest(InstanceMixin, IntegrationTest):
    @classmethod
    def setUpClass(cls):
        super(DataEndpointIntegrationTest, cls).setUpClass()
        cls.klass = cls.instance.classes.create(
            name='sample_klass',
            schema=[
                {'name': 'test1', 'type': 'string', 'filter_index': True},
                {'name': 'test2', 'type': 'string', 'filter_index': True},
                {'name': 'test3', 'type': 'integer', 'filter_index': True},
            ])

        cls.data_object = cls.klass.objects.create(
            class_name=cls.klass.name,
            test1='atest',
            test2='321',
            test3=50
        )

        cls.data_object = cls.klass.objects.create(
            class_name=cls.klass.name,
            test1='btest',
            test2='432',
            test3=45
        )

        cls.data_object = cls.klass.objects.create(
            class_name=cls.klass.name,
            test1='ctest',
            test2='543',
            test3=35
        )

        cls.data_endpoint = cls.instance.data_endpoints.create(
            name='test_data_endpoint',
            description='test description',
            class_name=cls.klass.name,
            query={'test3': {'_gt': 35}}
        )

    def test_mapping_class_name_lib_creation(self):
        data_endpoint = DataEndpoint(
            name='yet_another_data_endpoint',
            class_name=self.klass.name,
        )
        data_endpoint.save()
        self.assertEqual(data_endpoint.class_name, 'sample_klass')

    def test_mapping_class_name_lib_read(self):
        data_endpoint = self.instance.data_endpoints.get(name='test_data_endpoint')
        self.assertEqual(data_endpoint.class_name, 'sample_klass')

    def test_data_endpoint_filtering(self):
        data_endpoint = self.instance.data_endpoints.get(name='test_data_endpoint')
        objects = [object for object in data_endpoint.get()]
        self.assertEqual(len(objects), 2)

        objects = [object for object in data_endpoint.get(test1__eq='atest')]
        self.assertEqual(len(objects), 1)

    def test_backward_compatibility_name(self):
        from syncano.models import EndpointData

        data_endpoint = EndpointData.please.get(name='test_data_endpoint')
        self.assertEqual(data_endpoint.class_name, 'sample_klass')
