from __future__ import unicode_literals

from syncano import logger
from syncano.exceptions import SyncanoValueError, SyncanoValidationError
from .options import Options
from .fields import Field, ModelField, ObjectField, MAPPING


class Registry(object):

    def __init__(self, connection, models=None):
        self.connection = connection
        self.models = models or []

    def __str__(self):
        return 'Registry: {0}'.format(', '.join(self.models))

    def __unicode__(self):
        return unicode(str(self))

    def register_model(self, name, cls):
        if name not in self.models:
            logger.debug('Registry: %s', name)
            self.models.append(name)
            setattr(self, str(name), cls)
        return self

    def register_definition(self, definition, model_ids=None):
        Meta = type(str('Meta'), (Options, ), {
            'connection': self.connection,
            'endpoints': definition['endpoints'],
            'name': definition['name'],
            'id': definition['id'],
        })

        attrs = {
            'Meta': Meta,
            'links': ObjectField(read_only=True, required=False)
        }
        for name, options in definition.get('properties', {}).iteritems():
            field_type = options.pop('type')

            if field_type in model_ids:
                field_attr = ModelField(field_type, **options)
            elif field_type in MAPPING:
                field_attr = MAPPING[field_type](**options)
            else:
                raise SyncanoValueError('Invalid field type "{0}".'.format(field_type))

            attrs[name] = field_attr

        cls = type(str(definition['name']), (Model, ), attrs)
        self.register_model(definition['name'], cls)

        return self

    def register_schema(self, schema):
        model_ids = [definition['id'] for definition in schema]

        for definition in schema:
            self.register_definition(definition, model_ids)

        return self


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

        # Find all descriptors, auto-set their names
        for n, v in attrs.iteritems():
            if isinstance(v, Field):
                v.name = n
                new_class.add_to_class(n, v)
                meta.add_field(v)

        return new_class

    def add_to_class(cls, name, value):
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
                field.validate(value)

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
