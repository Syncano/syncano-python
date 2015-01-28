from __future__ import unicode_literals

import six
import inspect

from syncano.exceptions import SyncanoValidationError, SyncanoDoesNotExist
from .options import Options
from .manager import Manager


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        super_new = super(ModelMetaclass, cls).__new__

        parents = [b for b in bases if isinstance(b, ModelMetaclass)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        module = attrs.pop('__module__', None)
        new_class = super_new(cls, name, bases, {'__module__': module})

        meta = attrs.pop('Meta', None) or getattr(new_class, 'Meta', None)
        meta = Options(meta)
        new_class.add_to_class('_meta', meta)

        manager = attrs.pop('please', Manager())
        new_class.add_to_class('please', manager)

        error_class = new_class.create_error_class()
        new_class.add_to_class('DoesNotExist', error_class)

        for n, v in six.iteritems(attrs):
            new_class.add_to_class(n, v)

        return new_class

    def add_to_class(cls, name, value):
        if not inspect.isclass(value) and hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

    def create_error_class(cls):
        return type(
            str('{0}DoesNotExist'.format(cls.__name__)),
            (SyncanoDoesNotExist, ),
            {}
        )


@six.add_metaclass(ModelMetaclass)
class Model(object):

    def __init__(self, **kwargs):
        self._reset()
        self.to_python(kwargs)
        self.build_properties(kwargs)

    def save(self, **kwargs):
        self.validate()
        data = self.to_native()

        if self.links:
            endpoint = self.links['self']
            method = 'PUT'
        else:
            self.build_properties(kwargs)
            endpoint = self._meta.resolve_endpoint('list', self._properties)
            method = 'POST'

        request = {'data': data}
        response = self._meta.connection.request(method, endpoint, **request)

        self.to_python(response)
        self.build_properties(response)

        return self

    def delete(self):
        if not self.links:
            raise SyncanoValidationError('Method allowed only on existing model.')

        endpoint = self.links['self']
        self._meta.connection.request('DELETE', endpoint)
        self._reset()

    def validate(self):
        for field in self._meta.fields:
            if not field.read_only:
                value = getattr(self, field.name)
                field.validate(value, self)

    def is_valid(self):
        try:
            self.validate()
            return True
        except SyncanoValidationError:
            return False

    def to_python(self, data):
        for field in self._meta.fields:
            if field.name in data:
                value = data[field.name]
                setattr(self, field.name, value)

    def to_native(self):
        data = {}
        for field in self._meta.fields:
            if not field.read_only:
                value = getattr(self, field.name)
                data[field.name] = field.to_native(value)
        return data

    def build_properties(self, data):
        properties = self._meta.get_endpoint_properties('detail')
        field_names = [field.name for field in self._meta.fields]
        for prop_name in properties:
            if prop_name in field_names:
                self._properties[prop_name] = getattr(self, prop_name)
            elif prop_name in data:
                self._properties[prop_name] = data[prop_name]

    def _reset(self):
        self._raw_data = {}
        self._properties = {}
