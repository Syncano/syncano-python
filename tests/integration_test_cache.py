# -*- coding: utf-8 -*-
from syncano.models import RuntimeChoices
from tests.integration_test import InstanceMixin, IntegrationTest


class DataEndpointCacheTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(DataEndpointCacheTest, cls).setUpClass()
        cls.klass = cls.instance.classes.create(
            name='sample_klass',
            schema=[
                {'name': 'test1', 'type': 'string'},
                {'name': 'test2', 'type': 'string'}
            ])

        cls.data_object = cls.klass.objects.create(
            class_name=cls.klass.name,
            test1='123',
            test2='321',
        )

        cls.data_endpoint = cls.instance.data_endpoints.create(
            name='test_data_endpoint',
            description='test description',
            class_name=cls.klass.name,
            query={}
        )

    def test_cache_request(self):
        data_endpoint = list(self.data_endpoint.get(cache_key='12345'))

        self.assertTrue(data_endpoint)

        for data_object in data_endpoint:
            self.assertTrue(data_object)


class ScriptEndpointCacheTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(ScriptEndpointCacheTest, cls).setUpClass()

        cls.script = cls.instance.scripts.create(
            label='test_script',
            description='test script desc',
            source='print(12)',
            runtime_name=RuntimeChoices.PYTHON_V5_0,
        )

        cls.script_endpoint = cls.instance.script_endpoints.create(
            name='test_script_endpoint',
            script=cls.script.id
        )

    def test_cache_request(self):
        response = self.script_endpoint.run(cache_key='123456')
        self.assertEqual(response.result['stdout'], '12')
