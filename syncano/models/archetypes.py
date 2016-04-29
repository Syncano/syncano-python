

import inspect

import six
from syncano.exceptions import SyncanoDoesNotExist, SyncanoValidationError

from . import fields
from .manager import Manager
from .options import Options
from .registry import registry


class ModelMetaclass(type):
    """Metaclass for all models.
    """
    def __new__(cls, name, bases, attrs):
        super_new = super(ModelMetaclass, cls).__new__

        parents = [b for b in bases if isinstance(b, ModelMetaclass)]
        abstracts = [b for b in bases if hasattr(b, 'Meta') and getattr(b.Meta, 'abstract', None)]
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

        for abstract in abstracts:
            for n, v in six.iteritems(abstract.__dict__):
                if isinstance(v, fields.Field) or n in ['LINKS']:  # extend this condition if required;
                    new_class.add_to_class(n, v)

        if not meta.pk:
            pk_field = fields.IntegerField(primary_key=True, read_only=True,
                                           required=False)
            new_class.add_to_class('id', pk_field)

        for field_name in meta.endpoint_fields:
            if field_name not in meta.field_names:
                endpoint_field = fields.EndpointField()
                new_class.add_to_class(field_name, endpoint_field)

        new_class.build_doc(name, meta)
        registry.add(name, new_class)
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

    def build_doc(cls, name, meta):
        """Give the class a docstring if it's not defined.
        """
        if cls.__doc__ is not None:
            return

        field_names = ['{0} = {1}'.format(f.name, f.__class__.__name__) for f in meta.fields]
        cls.__doc__ = '{0}:\n\t{1}'.format(name, '\n\t'.join(field_names))


class Model(six.with_metaclass(ModelMetaclass)):
    """Base class for all models.
    """

    def __init__(self, **kwargs):
        self.is_lazy = kwargs.pop('is_lazy', False)
        self._raw_data = {}
        self.to_python(kwargs)

    def __repr__(self):
        """Displays current instance class name and pk.
        """
        return '<{0}: {1}>'.format(
            self.__class__.__name__,
            self.pk
        )

    def __str__(self):
        """Wrapper around ```repr`` method.
        """
        return repr(self)

    def __unicode__(self):
        """Wrapper around ```repr`` method with proper encoding.
        """
        return six.u(repr(self))

    def __eq__(self, other):
        if isinstance(other, Model):
            return self.pk == other.pk
        return NotImplemented

    def _get_connection(self, **kwargs):
        connection = kwargs.pop('connection', None)
        return connection or self._meta.connection

    def save(self, **kwargs):
        """
        Creates or updates the current instance.
        Override this in a subclass if you want to control the saving process.
        """
        self.validate()
        data = self.to_native()
        connection = self._get_connection(**kwargs)
        properties = self.get_endpoint_data()
        endpoint_name = 'list'
        method = 'POST'

        if not self.is_new():
            endpoint_name = 'detail'
            methods = self._meta.get_endpoint_methods(endpoint_name)
            if 'put' in methods:
                method = 'PUT'

        endpoint = self._meta.resolve_endpoint(endpoint_name, properties)
        if 'expected_revision' in kwargs:
            data.update({'expected_revision': kwargs['expected_revision']})
        request = {'data': data}

        if not self.is_lazy:
            response = connection.request(method, endpoint, **request)
            self.to_python(response)
            return self

        return self.batch_object(method=method, path=endpoint, body=request['data'], properties=data)

    @classmethod
    def batch_object(cls, method, path, body, properties=None):
        properties = properties if properties else {}
        return {
            'body': {
                'method': method,
                'path': path,
                'body': body,
            },
            'meta': {
                'model': cls,
                'properties': properties
            }
        }

    def mark_for_batch(self):
        self.is_lazy = True

    def delete(self, **kwargs):
        """Removes the current instance.
        """
        if self.is_new():
            raise SyncanoValidationError('Method allowed only on existing model.')

        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('detail', properties)
        connection = self._get_connection(**kwargs)
        connection.request('DELETE', endpoint)
        if self.__class__.__name__ == 'Instance':  # avoid circular import;
            registry.clear_used_instance()
        self._raw_data = {}

    def reload(self, **kwargs):
        """Reloads the current instance.
        """
        if self.is_new():
            raise SyncanoValidationError('Method allowed only on existing model.')

        properties = self.get_endpoint_data()
        endpoint = self._meta.resolve_endpoint('detail', properties)
        connection = self._get_connection(**kwargs)
        response = connection.request('GET', endpoint)
        self.to_python(response)

    def validate(self):
        """
        Validates the current instance.

        :raises: SyncanoValidationError, SyncanoFieldError
        """
        for field in self._meta.fields:
            if not field.read_only:
                value = getattr(self, field.name)
                field.validate(value, self)

    def is_valid(self):
        try:
            self.validate()
        except SyncanoValidationError:
            return False
        else:
            return True

    def is_new(self):
        if 'links' in self._meta.field_names:
            return not self.links

        if self._meta.pk.read_only and not self.pk:
            return True

        return False

    def to_python(self, data):
        """
        Converts raw data to python types and built-in objects.

        :type data: dict
        :param data: Raw data
        """
        for field in self._meta.fields:
            field_name = field.name

            if field.mapping is not None and self.pk:
                field_name = field.mapping

            if field_name in data:
                value = data[field_name]
                setattr(self, field.name, value)

            if isinstance(field, fields.RelationField):
                setattr(self, "{}_set".format(field_name), field(instance=self, field_name=field_name))

    def to_native(self):
        """Converts the current instance to raw data which
        can be serialized to JSON and send to API.
        """
        data = {}
        for field in self._meta.fields:
            if not field.read_only and field.has_data:
                value = getattr(self, field.name)
                if value is None and field.blank:
                    continue

                if field.mapping:
                    data[field.mapping] = field.to_native(value)
                else:

                    param_name = getattr(field, 'param_name', field.name)
                    if param_name == 'files' and param_name in data:
                        data[param_name].update(field.to_native(value))
                    else:
                        data[param_name] = field.to_native(value)
        return data

    def get_endpoint_data(self):
        properties = {}
        for field in self._meta.fields:
            if field.has_endpoint_data:
                properties[field.name] = getattr(self, field.name)
        return properties
