import re
import six

from functools import partial

from syncano.exceptions import SyncanoValidationError


class Field(object):

    def __init__(self, name=None, **kwargs):
        self.name = name
        self.description = kwargs.pop('description', None)
        self.format = kwargs.pop('format', None)
        self.required = kwargs.pop('required', True)
        self.read_only = kwargs.pop('readOnly', False) or kwargs.pop('read_only', False)
        self.default = kwargs.pop('defaultValue', None) or kwargs.pop('default', None)
        self.schema = kwargs

    def __get__(self, instance, owner):
        return instance._raw_data.get(self.name, self.default)

    def __set__(self, instance, value):
        self.validate(value)
        instance._raw_data[self.name] = self.to_python(value)

    def __delete__(self, instance):
        if self.name in instance._raw_data:
            del instance._raw_data[self.name]

    def validate(self, value):
        if self.required and not value:
            raise SyncanoValidationError('Field is required.')

    def to_python(self, value):
        return value

    def to_native(self, value):
        return value

    def attach_to_instance(self, instance):
        pass


class StringField(Field):

    def to_python(self, value):
        if isinstance(value, six.string_types) or value is None:
            return value
        return six.u(value)


class IntegerField(Field):

    def to_python(self, value):
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise SyncanoValidationError('Invalid value.')


class FloatField(Field):

    def to_python(self, value):
        if value is None:
            return value
        try:
            return float(value)
        except (TypeError, ValueError):
            raise SyncanoValidationError('Invalid value.')


class BooleanField(Field):

    def to_python(self, value):
        if value in (True, False):
            return bool(value)

        if value in ('t', 'True', '1'):
            return True

        if value in ('f', 'False', '0'):
            return False

        raise SyncanoValidationError('Invalid value.')


class SlugField(StringField):
    regex = re.compile(r'^[-a-zA-Z0-9_]+$')

    def validate(self, value):
        super(SlugField, self).validate(value)
        if not bool(self.regex.search(value)):
            raise SyncanoValidationError('Invalid value.')
        return value


class EmailField(StringField):
    regex = re.compile(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)')

    def validate(self, value):
        super(EmailField, self).validate(value)

        if not value or '@' not in value:
            raise SyncanoValidationError('Invalid value.')

        if not bool(self.regex.match(value)):
            raise SyncanoValidationError('Invalid value.')


class ChoiceField(Field):

    def __init__(self, *args, **kwargs):
        self.choices = kwargs.pop('enum', None) or kwargs.pop('choices', None)
        super(ChoiceField, self).__init__(*args, **kwargs)

    def validate(self, value):
        super(ChoiceField, self).validate(value)
        if self.choices and value not in self.choices:
            raise SyncanoValidationError('Invalid value.')


class DateField(Field):
    pass


class DateTimeField(DateField):
    pass


class ObjectField(Field):
    pass


class ModelField(ObjectField):
    def __init__(self, model_id, *args, **kwargs):
        self.model_id = model_id
        super(ModelField, self).__init__(*args, **kwargs)


class HyperlinkeField(ObjectField):
    METHOD_NAME = '_get_LINK'
    METHOD_PATTERN = 'get_{name}'
    IGNORED_LINKS = ('self', )

    def attach_to_instance(self, instance):
        super(HyperlinkeField, self).attach_to_instance(instance)
        links = getattr(instance, self.name)
        method = getattr(instance, self.METHOD_NAME)

        for name, path in links.iteritems():
            if name in self.IGNORED_LINKS:
                continue

            method_name = self.METHOD_PATTERN.format(name=name)
            partial_method = partial(method, field=self, name=name)
            setattr(instance, method_name, partial_method)


MAPPING = {
    'string': StringField,
    'integer': IntegerField,
    'float': FloatField,
    'boolean': BooleanField,
    'slug': SlugField,
    'email': EmailField,
    'choice': ChoiceField,
    'date': DateField,
    'datetime': DateTimeField,
    'field': ObjectField,
}
