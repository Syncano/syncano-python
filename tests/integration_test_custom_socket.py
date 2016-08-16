# -*- coding: utf-8 -*-
import time

from syncano.models import (
    CustomSocket,
    Endpoint,
    RuntimeChoices,
    Script,
    ScriptCall,
    ScriptDependency,
    ScriptEndpoint,
    SocketEndpoint
)
from tests.integration_test import InstanceMixin, IntegrationTest


class CustomSocketTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(CustomSocketTest, cls).setUpClass()
        cls.custom_socket = cls._create_custom_socket('default', cls._define_dependencies_new_script_endpoint)
        cls._assert_custom_socket(cls.custom_socket)

    def test_publish_custom_socket(self):
        # this test new ScriptEndpoint dependency create;
        self.assert_custom_socket('publishing', self._define_dependencies_new_script_endpoint)

    def test_dependencies_new_script(self):
        self.assert_custom_socket('new_script_publishing', self._define_dependencies_new_script)

    def test_dependencies_existing_script(self):
        self.assert_custom_socket('existing_script_publishing', self._define_dependencies_existing_script)

    def test_dependencies_existing_script_endpoint(self):
        self.assert_custom_socket('existing_script_e_publishing',
                                  self._define_dependencies_existing_script_endpoint)

    def test_creating_raw_data(self):
        custom_socket = CustomSocket.please.create(
            name='my_custom_socket_123',
            endpoints={
                "my_custom_endpoint_123": {
                    "calls": [{"type": "script", "name": "script_123", "methods": ["POST"]}]
                }
            },
            dependencies=[
                {
                    "type": "script",
                    "runtime_name": "python_library_v5.0",
                    "name": "script_123",
                    "source": "print(123)"
                }
            ]
        )

        self.assertTrue(custom_socket.name)

    def test_custom_socket_run(self):
        results = self.custom_socket.run('my_endpoint_default')
        self.assertEqual(results.result['stdout'], 'script_default')

    def test_custom_socket_recheck(self):
        custom_socket = self.custom_socket.recheck()
        self.assertTrue(custom_socket.name)

    def test_fetching_all_endpoints(self):
        all_endpoints = SocketEndpoint.get_all_endpoints()
        self.assertTrue(isinstance(all_endpoints, list))
        self.assertTrue(len(all_endpoints) >= 1)
        self.assertTrue(all_endpoints[0].name)

    def test_endpoint_run(self):
        script_endpoint = SocketEndpoint.get_all_endpoints()[0]
        result = script_endpoint.run()
        suffix = script_endpoint.name.split('_')[-1]
        self.assertTrue(result.result['stdout'].endswith(suffix))

    def test_custom_socket_update(self):
        socket_to_update = self._create_custom_socket('to_update', self._define_dependencies_new_script_endpoint)
        socket_to_update.remove_endpoint(endpoint_name='my_endpoint_to_update')

        new_endpoint = Endpoint(name='my_endpoint_new_to_update')
        new_endpoint.add_call(
            ScriptCall(name='script_default', methods=['GET'])
        )

        socket_to_update.add_endpoint(new_endpoint)
        socket_to_update.update()
        time.sleep(2)  # wait for custom socket setup;
        socket_to_update.reload()
        self.assertIn('my_endpoint_new_to_update', socket_to_update.endpoints)

    def assert_custom_socket(self, suffix, dependency_method):
        custom_socket = self._create_custom_socket(suffix, dependency_method=dependency_method)
        self._assert_custom_socket(custom_socket)

    @classmethod
    def _assert_custom_socket(cls, custom_socket):
        cls.assertTrue(custom_socket.name)
        cls.assertTrue(custom_socket.created_at)
        cls.assertTrue(custom_socket.updated_at)

    @classmethod
    def _create_custom_socket(cls, suffix, dependency_method):
        custom_socket = CustomSocket(name='my_custom_socket_{}'.format(suffix))

        cls._define_endpoints(suffix, custom_socket)
        dependency_method(suffix, custom_socket)

        custom_socket.publish()
        return custom_socket

    @classmethod
    def _define_endpoints(cls, suffix, custom_socket):
        endpoint = Endpoint(name='my_endpoint_{}'.format(suffix))
        endpoint.add_call(
            ScriptCall(
                name='script_{}'.format(suffix),
                methods=['GET', 'POST']
            )
        )
        custom_socket.add_endpoint(endpoint)

    @classmethod
    def _define_dependencies_new_script_endpoint(cls, suffix, custom_socket):
        script = cls._create_script(suffix)
        script_endpoint = ScriptEndpoint(
            name='script_endpoint_{}'.format(suffix),
            script=script.id
        )
        custom_socket.add_dependency(
            ScriptDependency(
                script_endpoint
            )
        )

    @classmethod
    def _define_dependencies_new_script(cls, suffix, custom_socket):
        custom_socket.add_dependency(
            ScriptDependency(
                Script(
                    source='print({})'.format(suffix),
                    runtime_name=RuntimeChoices.PYTHON_V5_0
                ),
                name='script_endpoint_{}'.format(suffix),
            )
        )

    @classmethod
    def _define_dependencies_existing_script(cls, suffix, custom_socket):
        # create Script first:
        cls._create_script(suffix)
        custom_socket.add_dependency(
            ScriptDependency(
                Script.please.first(),
                name='script_endpoint_{}'.format(suffix),
            )
        )

    @classmethod
    def _define_dependencies_existing_script_endpoint(cls, suffix, custom_socket):
        script = cls._create_script(suffix)
        ScriptEndpoint.please.create(
            name='script_endpoint_{}'.format(suffix),
            script=script.id
        )
        custom_socket.add_dependency(
            ScriptDependency(
                ScriptEndpoint.please.first()
            )
        )

    @classmethod
    def _create_script(cls, suffix):
        return Script.please.create(
            label='script_{}'.format(suffix),
            runtime_name=RuntimeChoices.PYTHON_V5_0,
            source='print({})'.format(suffix)
        )
