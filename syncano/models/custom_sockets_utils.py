# -*- coding: utf-8 -*-
import six
from syncano.exceptions import SyncanoValueError

from .incentives import Script


class CallTypeE(object):
    """
    The type of the call object used in the custom socket;
    """
    SCRIPT = 'script'


class DependencyTypeE(object):
    """
    The type of the dependency object used in the custom socket;
    """
    SCRIPT = 'script'


class BaseCall(object):
    """
    Base class for call object.
    """

    call_type = None

    def __init__(self, name, methods):
        self.name = name
        self.methods = methods

    def to_dict(self):
        if self.call_type is None:
            raise SyncanoValueError('call_type not set.')
        return {
            'type': self.call_type,
            'name': self.name,
            'methods': self.methods
        }


class ScriptCall(BaseCall):
    """
    Script call object.

    The JSON format is as follows (to_dict in the base class)::

        {
            'type': 'script',
            'name': '<script_label>,
            'methods': [<method_list>],
        }

    methods can be as follows:
        * ['GET']
        * ['*'] - which will do a call on every request method;
    """
    call_type = CallTypeE.SCRIPT


class Endpoint(object):
    """
    The object which stores metadata about endpoints in custom socket;

    The JSON format is as follows::

        {
            '<endpoint_name>: {
                'calls': [
                    <list of JSON format of Calls objects>
                ]
            }
        }

    """
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
    """
    Base dependency object;

    On the base of the fields attribute - the JSON format of the dependency is returned.
    The fields are taken from the dependency object - which can be Script (supported now).
    """

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
    """
    Script dependency object;

    The JSON format is as follows::
        {
            'type': 'script',
            'runtime_name': '<runtime name defined in RuntimeChoices>',
        }
    """
    dependency_type = DependencyTypeE.SCRIPT
    fields = [
        'runtime_name',
        'name',
        'source'
    ]

    field_mapping = {'name': 'label'}
    id_name = 'label'


class EndpointMetadataMixin(object):
    """
    A mixin which allows to collect Endpoints objects and transform them to the appropriate JSON format.
    """

    def __init__(self, *args, **kwargs):
        self._endpoints = []
        super(EndpointMetadataMixin, self).__init__(*args, **kwargs)
        if self.endpoints:
            self.update_endpoints()

    def update_endpoints(self):
        for raw_endpoint_name, raw_endpoint in six.iteritems(self.endpoints):
            endpoint = Endpoint(
                name=raw_endpoint_name,
            )
            for call in raw_endpoint['calls']:
                call_class = self._get_call_class(call['type'])
                call_instance = call_class(name=call['name'], methods=call['methods'])
                endpoint.add_call(call_instance)

            self.add_endpoint(endpoint)

    @classmethod
    def _get_call_class(cls, call_type):
        if call_type == CallTypeE.SCRIPT:
            return ScriptCall

    def add_endpoint(self, endpoint):
        self._endpoints.append(endpoint)

    def remove_endpoint(self, endpoint_name):
        for index, endpoint in enumerate(self._endpoints):
            if endpoint.name == endpoint_name:
                self._endpoints.pop(index)
                break

    @property
    def endpoints_data(self):
        endpoints = {}
        for endpoint in self._endpoints:
            endpoints.update(endpoint.to_endpoint_data())
        return endpoints


class DependencyMetadataMixin(object):
    """
    A mixin which allows to collect Dependencies objects and transform them to the appropriate JSON format.
    """

    def __init__(self, *args, **kwargs):
        self._dependencies = []
        super(DependencyMetadataMixin, self).__init__(*args, **kwargs)
        if self.dependencies:
            self.update_dependencies()

    def update_dependencies(self):
        for raw_depedency in self.dependencies:
            depedency_class, object_class = self._get_depedency_klass(raw_depedency['type'])

            self.add_dependency(depedency_class(
                object_class(**{
                    depedency_class.field_mapping.get(field_name, field_name): raw_depedency.get(field_name)
                    for field_name in depedency_class.fields
                })
            ))

    @classmethod
    def _get_depedency_klass(cls, depedency_type):
        if depedency_type == DependencyTypeE.SCRIPT:
            return ScriptDependency, Script

    def add_dependency(self, depedency):
        self._dependencies.append(depedency)

    def remove_dependency(self, dependency_name):
        for index, dependency in enumerate(self._dependencies):
            if dependency_name == getattr(dependency.dependency_object, dependency.id_name, None):
                self._dependencies.pop(index)
                break

    @property
    def dependencies_data(self):
        return [dependency.to_dependency_data() for dependency in self._dependencies]
