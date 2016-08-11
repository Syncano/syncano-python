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
    :ivar links: :class:`~syncano.models.fields.LinksField`
    """

    name = fields.StringField(max_length=64, primary_key=True)
    endpoints = fields.JSONField()
    dependencies = fields.JSONField()
    metadata = fields.JSONField(read_only=True, required=False)
    status = fields.StringField(read_only=True, required=False)
    status_info = fields.StringField(read_only=True, required=False)
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
        endpoints_path = self.links.endpoints
        connection = self._get_connection()
        response = connection.request('GET', endpoints_path)
        endpoints = []
        for endpoint in response['objects']:
            endpoints.append(SocketEndpoint(**endpoint))
        return endpoints

    def run(self, method, endpoint_name, data={}):
        endpoint = self._find_endpoint(endpoint_name)
        return endpoint.run(method, data=data)

    def _find_endpoint(self, endpoint_name):
        endpoints = self.get_endpoints()
        for endpoint in endpoints:
            if endpoint_name == endpoint.name:
                return endpoint
        raise SyncanoValueError('Endpoint {} not found.'.format(endpoint_name))

    def publish(self):
        if not self.is_new():
            raise SyncanoValueError('Can not publish already defined custom socket.')

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
            raise SyncanoValueError('Publish socket first.')

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
    calls = fields.JSONField()
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

    def run(self, method='GET', data={}):
        endpoint_path = self.links.endpoint
        connection = self._get_connection()
        if not self._validate_method(method):
            raise SyncanoValueError('Method: {} not specified in calls for this custom socket.'.format(method))

        if method in ['GET', 'DELETE']:
            response = connection.request(method, endpoint_path)
        elif method in ['POST', 'PUT', 'PATCH']:
            response = connection.request(method, endpoint_path, data=data)
        else:
            raise SyncanoValueError('Method: {} not supported.'.format(method))
        return response

    def _validate_method(self, method):

        methods = []
        for call in self.calls:
            methods.extend(call['methods'])
        if '*' in methods or method in methods:
            return True
        return False
