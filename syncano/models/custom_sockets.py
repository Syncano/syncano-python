# -*- coding: utf-8 -*-
from .base import Instance, Model
from . import fields

from syncano.exceptions import SyncanoValueError


class CallTypeE(object):
    SCRIPT = 'script'


class DependencyTypeE(object):
    SCRIPT = 'script'


class Call(object):

    def __init__(self, name, methods, call_type=None):
        call_type = call_type or CallTypeE.SCRIPT
        self.type = call_type
        self.name = name
        self.methods = methods

    def to_dict(self):
        return {
            'type': self.type,
            'name': self.name,
            'methods': self.methods
        }


class Endpoint(object):

    def __init__(self, name):
        self.name = name
        self.calls = []

    def add_call(self, call):
        self.calls.append(call)

    def to_endpoint_data(self):
        return {
            self.name: {
                'calls': [call.to_dict() for call in self.calls]
            }
        }


class BaseDependency(object):

    fields = []
    dependency_type = None
    field_mapping = {}

    def __init__(self, dependency_object):
        self.dependency_object = dependency_object

    def to_dependency_data(self):
        if self.dependency_type is None:
            raise SyncanoValueError('dependency_type not set.')
        dependency_data = {'type': self.dependency_type}
        dependency_data.update({field_name: getattr(
            self.dependency_object,
            self.field_mapping.get(field_name, field_name)
        ) for field_name in self.fields})
        return dependency_data


class ScriptDependency(BaseDependency):
    dependency_type = DependencyTypeE.SCRIPT
    fields = [
        'runtime_name',
        'name',
        'source'
    ]

    field_mapping = {'name': 'label'}


class EndpointMetadataMixin(object):

    def __init__(self, *args, **kwargs):
        self._endpoints = []
        super(EndpointMetadataMixin, self).__init__(*args, **kwargs)

    def add_endpoint(self, endpoint):
        self._endpoints.append(endpoint)

    @property
    def endpoints_data(self):
        endpoints = {}
        for endpoint in self._endpoints:
            endpoints.update(endpoint.to_endpoint_data())
        return endpoints


class DependencyMetadataMixin(object):

    def __init__(self, *args, **kwargs):
        self._dependencies = []
        super(DependencyMetadataMixin, self).__init__(*args, **kwargs)

    def add_dependency(self, depedency):
        self._dependencies.append(depedency)

    @property
    def dependencies_data(self):
        return [dependency.to_dependency_data() for dependency in self._dependencies]


class CustomSocket(EndpointMetadataMixin, DependencyMetadataMixin, Model):
    """
    OO wrapper around instance custom sockets.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar endpoints: :class:`~syncano.models.fields.JSONField`
    :ivar dependencies: :class:`~syncano.models.fields.JSONField`
    :ivar metadata: :class:`~syncano.models.fields.JSONField`
    :ivar links: :class:`~syncano.models.fields.LinksField`
    """

    name = fields.StringField(max_length=64)
    endpoints = fields.JSONField()
    dependencies = fields.JSONField()
    metadata = fields.JSONField(read_only=True, required=False)
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
            print(endpoint.name, endpoint_name)
            if endpoint_name == endpoint.name:
                return endpoint
        raise SyncanoValueError('Endpoint {} not found.'.format(endpoint_name))

    def publish(self):
        created_socket = self.__class__.please.create(
            name=self.name,
            endpoints=self.endpoints_data,
            dependencies=self.dependencies_data
        )
        raw_data = created_socket._raw_data
        raw_data['links'] = raw_data['links'].links_dict
        self.to_python(raw_data)
        return self


class SocketEndpoint(Model):
    """
    OO wrapper around endpoints defined in CustomSocket instance.

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

        if method == ['GET', 'DELETE']:
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
