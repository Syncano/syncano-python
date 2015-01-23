import re
import six

from functools import partial

from syncano.exceptions import SyncanoFieldError


class Field(object):

    def __init__(self, name=None, **kwargs):
        self.name = name
        self.model = None
        self.label = kwargs.pop('label', None)

        self.required = kwargs.pop('required', True)
        self.read_only = kwargs.pop('read_only', False)
        self.default = kwargs.pop('default', None)

        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)

        self.schema = kwargs

    def __get__(self, instance, owner):
        return instance._raw_data.get(self.name, self.default)

    def __set__(self, instance, value):
        self.validate(value, instance)
        instance._raw_data[self.name] = self.to_python(value)

    def __delete__(self, instance):
        if self.name in instance._raw_data:
            del instance._raw_data[self.name]

    def validate(self, value, model_instance):
        if self.required and not value:
            raise SyncanoFieldError(self.name, 'Field is required.')

        if self.read_only and getattr(model_instance, self.name):
            raise SyncanoFieldError(self.name, 'Field is read only.')

    def to_python(self, value):
        return value

    def to_native(self, value):
        return value

    def contribute_to_class(self, cls, name):
        self.model = cls
        cls._meta.add_field(self)

        if not self.name:
            self.name = name

        setattr(cls, name, self)


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
            raise SyncanoFieldError(self.name, 'Invalid value.')


class FloatField(Field):

    def to_python(self, value):
        if value is None:
            return value
        try:
            return float(value)
        except (TypeError, ValueError):
            raise SyncanoFieldError(self.name, 'Invalid value.')


class BooleanField(Field):

    def to_python(self, value):
        if value in (True, False):
            return bool(value)

        if value in ('t', 'True', '1'):
            return True

        if value in ('f', 'False', '0'):
            return False

        raise SyncanoFieldError(self.name, 'Invalid value.')


class SlugField(StringField):
    regex = re.compile(r'^[-a-zA-Z0-9_]+$')

    def validate(self, value, model_instance):
        super(SlugField, self).validate(value, model_instance)
        if not bool(self.regex.search(value)):
            raise SyncanoFieldError(self.name, 'Invalid value.')
        return value


class EmailField(StringField):
    regex = re.compile(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)')

    def validate(self, value, model_instance):
        super(EmailField, self).validate(value, model_instance)

        if not value or '@' not in value:
            raise SyncanoFieldError(self.name, 'Invalid value.')

        if not bool(self.regex.match(value)):
            raise SyncanoFieldError(self.name, 'Invalid value.')


class ChoiceField(Field):

    def __init__(self, *args, **kwargs):
        self.choices = kwargs.pop('choices', [])
        self.allowed_values = [choice['value'] for choice in self.choices]
        super(ChoiceField, self).__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        super(ChoiceField, self).validate(value, model_instance)
        if self.choices and value not in self.allowed_values:
            raise SyncanoFieldError(self.name, 'Invalid choice.')


class DateField(Field):
    pass


class DateTimeField(DateField):
    pass


class ObjectField(Field):
    pass


class HyperlinkedField(ObjectField):
    METHOD_NAME = '_LINK'
    METHOD_PATTERN = 'get_{name}'
    IGNORED_LINKS = ('self', )

    def __init__(self, *args, **kwargs):
        self.links = kwargs.pop('links', [])
        super(HyperlinkedField, self).__init__(*args, **kwargs)

    # def contribute_to_class(self, cls, name):
    #     super(HyperlinkedField, self).contribute_to_class(cls, name)
    #     method = getattr(cls, self.METHOD_NAME)

    #     for link in self.links:
    #         if link['name'] in self.IGNORED_LINKS:
    #             continue

    #         method_name = self.METHOD_PATTERN.format(**link)
    #         partial_method = partial(method, field=self, name=link['name'])
    #         setattr(cls, method_name, partial_method)


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
    'field': Field,
    'links': HyperlinkedField,
}
