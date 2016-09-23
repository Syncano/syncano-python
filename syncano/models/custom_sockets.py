# -*- coding: utf-8 -*-
from syncano.exceptions import SyncanoValueError
from syncano.models.custom_sockets_utils import DependencyMetadataMixin, EndpointMetadataMixin

from . import fields
from .base import Instance, Model


class CustomSocket(EndpointMetadataMixin, DependencyMetadataMixin, Model):
    """
    OO wrapper around instance custom sockets.
    Look at the custom socket documentation for more details.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar endpoints: :class:`~syncano.models.fields.JSONField`
    :ivar dependencies: :class:`~syncano.models.fields.JSONField`
    :ivar metadata: :class:`~syncano.models.fields.JSONField`
    :ivar status: :class:`~syncano.models.fields.StringField`
    :ivar status_info: :class:`~syncano.models.fields.StringField`
    :ivar links: :class:`~syncano.models.fields.LinksField`
    """

    name = fields.StringField(max_length=64, primary_key=True)
    description = fields.StringField(required=False)
    endpoints = fields.JSONField()
    dependencies = fields.JSONField()
    metadata = fields.JSONField(required=False)
    config = fields.JSONField(required=False)
    status = fields.StringField(read_only=True, required=False)
    status_info = fields.StringField(read_only=True, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)
    links = fields.LinksField()

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['get', 'put', 'patch', 'delete'],
                'path': '/sockets/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/sockets/',
            }
        }

    def get_endpoints(self):
        return SocketEndpoint.get_all_endpoints(instance_name=self.instance_name)

    def run(self, endpoint_name, method='GET', data=None):
        endpoint = self._find_endpoint(endpoint_name)
        return endpoint.run(method=method, data=data or {})

    def _find_endpoint(self, endpoint_name):
        endpoints = self.get_endpoints()
        for endpoint in endpoints:
            if '{}/{}'.format(self.name, endpoint_name) == endpoint.name:
                return endpoint
        raise SyncanoValueError('Endpoint {} not found.'.format(endpoint_name))

    def install_from_url(self, url, instance_name=None, config=None):
        instance_name = self.__class__.please.properties.get('instance_name') or instance_name
        instance = Instance.please.get(name=instance_name)

        install_path = instance.links.sockets_install
        connection = self._get_connection()
        config = config or {}
        response = connection.request('POST', install_path, data={
            'name': self.name,
            'install_url': url,
            'config': config
        })

        return response

    def install(self):
        if not self.is_new():
            raise SyncanoValueError('Custom socket already installed.')

        created_socket = self.__class__.please.create(
            name=self.name,
            endpoints=self.endpoints_data,
            dependencies=self.dependencies_data
        )

        created_socket._raw_data['links'] = created_socket._raw_data['links'].links_dict
        self.to_python(created_socket._raw_data)
        return self

    def update(self):
        if self.is_new():
            raise SyncanoValueError('Install socket first.')

        update_socket = self.__class__.please.update(
            name=self.name,
            endpoints=self.endpoints_data,
            dependencies=self.dependencies_data
        )

        update_socket._raw_data['links'] = update_socket._raw_data['links'].links_dict
        self.to_python(update_socket._raw_data)
        return self

    def recheck(self):
        recheck_path = self.links.recheck
        connection = self._get_connection()
        rechecked_socket = connection.request('POST', recheck_path)
        self.to_python(rechecked_socket)
        return self


class SocketEndpoint(Model):
    """
    OO wrapper around endpoints defined in CustomSocket instance.
    Look at the custom socket documentation for more details.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar calls: :class:`~syncano.models.fields.JSONField`
    :ivar links: :class:`~syncano.models.fields.LinksField`
    """
    name = fields.StringField(max_length=64, primary_key=True)
    allowed_methods = fields.JSONField()
    links = fields.LinksField()

    class Meta:
        parent = CustomSocket
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/endpoints/{name}/'
            },
            'list': {
                'methods': ['get'],
                'path': '/endpoints/'
            }
        }

    def run(self, method='GET', data=None):
        endpoint_path = self.links.self
        connection = self._get_connection()
        if not self._validate_method(method):
            raise SyncanoValueError('Method: {} not specified in calls for this custom socket.'.format(method))
        method = method.lower()
        if method in ['get', 'delete']:
            response = connection.request(method, endpoint_path)
        elif method in ['post', 'put', 'patch']:
            response = connection.request(method, endpoint_path, data=data or {})
        else:
            raise SyncanoValueError('Method: {} not supported.'.format(method))
        return response

    @classmethod
    def get_all_endpoints(cls, instance_name=None):
        connection = cls._meta.connection
        all_endpoints_path = Instance._meta.resolve_endpoint(
            'endpoints',
            {'name': cls.please.properties.get('instance_name') or instance_name}
        )
        response = connection.request('GET', all_endpoints_path)
        return [cls(**endpoint) for endpoint in response['objects']]

    def _validate_method(self, method):
        if '*' in self.allowed_methods or method in self.allowed_methods:
            return True
        return False
