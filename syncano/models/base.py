from __future__ import unicode_literals

import inspect

from syncano.exceptions import SyncanoValidationError
from .options import Options


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

        for n, v in attrs.iteritems():
            new_class.add_to_class(n, v)

        return new_class

    def add_to_class(cls, name, value):
        if not inspect.isclass(value) and hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)


class Model(object):
    __metaclass__ = ModelMetaclass

    def __init__(self, **kwargs):
        self._raw_data = {}
        self.to_python(kwargs)

    @classmethod
    def make_request(cls, name, kwargs):
        path = cls._meta.resolve_endpoint(name, kwargs)
        params = cls._meta.get_endpoint_query_params(name, kwargs)
        request = {'result_class': cls, 'params': params}
        return cls._meta.connection.request('GET', path, **request)

    @classmethod
    def list(cls, **kwargs):
        return cls.make_request('list', kwargs)

    @classmethod
    def detail(cls, **kwargs):
        return cls.make_request('detail', kwargs)

    @classmethod
    def get(cls, **kwargs):
        return cls.detail(**kwargs)

    def save(self):
        self.validate()
        data = self.to_native()

        if self.links:
            endpoint = self.links['self']
        else:
            endpoint = self._meta.resolve_endpoint('list', data)

        request = {'data': data}
        response = self._meta.connection.request('POST', endpoint, **request)
        self.to_python(response)
        return self

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

    def to_python(self, kwargs):
        for field in self._meta.fields:
            if field.name in kwargs:
                value = kwargs[field.name]
                setattr(self, field.name, value)

    def to_native(self):
        data = {}
        for field in self._meta.fields:
            if not field.read_only:
                value = getattr(self, field.name)
                data[field.name] = field.to_native(value)
        return data
