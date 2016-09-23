# -*- coding: utf-8 -*-
import six
from syncano.exceptions import SyncanoValueError

from .classes import Class
from .incentives import Script, ScriptEndpoint


class CallType(object):
    """
    The type of the call object used in the custom socket;
    """
    SCRIPT = 'script'


class DependencyType(object):
    """
    The type of the dependency object used in the custom socket;
    """
    SCRIPT = 'script'
    CLASS = 'class'


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
    call_type = CallType.SCRIPT


class Endpoint(object):
    """
    The object which stores metadata about endpoints in custom socket;

    The JSON format is as follows::

        {
            '<endpoint_name>': {
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
    name = None

    def to_dependency_data(self):
        if self.dependency_type is None:
            raise SyncanoValueError('dependency_type not set.')
        dependency_data = {'type': self.dependency_type}
        dependency_data.update(self.get_dependency_data())
        return dependency_data

    def get_name(self):
        if self.name is not None:
            return {'name': self.name}
        return {'name': self.dependency_object.name}

    def get_dependency_data(self):
        raise NotImplementedError()

    def create_from_raw_data(self, raw_data):
        raise NotImplementedError()

    def _build_dict(self, instance):
        return {field_name: getattr(instance, field_name) for field_name in self.fields}


class ScriptDependency(BaseDependency):
    """
    Script dependency object;

    The JSON format is as follows::
        {
            'type': 'script',
            'runtime_name': '<runtime name defined in RuntimeChoices>',
            'source': '<source>',
            'name': '<name>'
        }
    """

    dependency_type = DependencyType.SCRIPT
    fields = [
        'runtime_name',
        'source'
    ]

    def __init__(self, script_or_script_endpoint, name=None):
        if not isinstance(script_or_script_endpoint, (Script, ScriptEndpoint)):
            raise SyncanoValueError('Script or ScriptEndpoint expected.')

        if isinstance(script_or_script_endpoint, Script) and not name:
            raise SyncanoValueError('Name should be provided.')

        self.dependency_object = script_or_script_endpoint
        self.name = name

    def get_dependency_data(self):

        if isinstance(self.dependency_object, ScriptEndpoint):
            script = Script.please.get(id=self.dependency_object.script,
                                       instance_name=self.dependency_object.instance_name)
        else:
            script = self.dependency_object

        dependency_data = self.get_name()
        dependency_data.update(self._build_dict(script))
        return dependency_data

    @classmethod
    def create_from_raw_data(cls, raw_data):
        return cls(**{
            'script_or_script_endpoint': Script(source=raw_data['source'], runtime_name=raw_data['runtime_name']),
            'name': raw_data['name'],
        })


class ClassDependency(BaseDependency):
    """
    Class dependency object;

    The JSON format is as follows::
        {
            'type': 'class',
            'name': '<class_name>',
            'schema': [
                {"name": "f1", "type": "string"},
                {"name": "f2", "type": "string"},
                {"name": "f3", "type": "integer"}
            ],
        }
    """
    dependency_type = DependencyType.CLASS
    fields = [
        'name',
        'schema'
    ]

    def __init__(self, class_instance):
        self.dependency_object = class_instance
        self.name = class_instance.name

    def get_dependency_data(self):
        data_dict = self._build_dict(self.dependency_object)
        data_dict['schema'] = data_dict['schema'].schema
        return data_dict

    @classmethod
    def create_from_raw_data(cls, raw_data):
        return cls(**{'class_instance': Class(**raw_data)})


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
        if call_type == CallType.SCRIPT:
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
            depedency_class = self._get_depedency_klass(raw_depedency['type'])
            self.add_dependency(depedency_class.create_from_raw_data(raw_depedency))

    @classmethod
    def _get_depedency_klass(cls, depedency_type):
        if depedency_type == DependencyType.SCRIPT:
            return ScriptDependency
        elif depedency_type == DependencyType.CLASS:
            return ClassDependency

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
