import re
import six
from datetime import date, datetime

from syncano.exceptions import SyncanoFieldError
from .manager import RelatedManagerDescriptor


class Field(object):
    required = False
    read_only = True
    default = None

    def __init__(self, name=None, **kwargs):
        self.name = name
        self.model = None
        self.default = kwargs.pop('default', self.default)
        self.required = kwargs.pop('required', self.required)
        self.read_only = kwargs.pop('read_only', self.read_only)
        self.label = kwargs.pop('label', None)
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
            raise self.VaidationError('This field is required.')

        if self.read_only and getattr(model_instance, self.name):
            raise self.VaidationError('Field is read only.')

        if isinstance(value, six.string_types):
            if self.max_length and len(value) > self.max_length:
                raise self.VaidationError('Max length reached.')

            if self.min_length and len(value) < self.min_length:
                raise self.VaidationError('Min length reached.')

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

        ErrorClass = type(
            '{0}VaidationError'.format(self.__class__.__name__),
            (SyncanoFieldError, ),
            {'field_name': name}
        )

        setattr(self, 'VaidationError', ErrorClass)


class WritableField(Field):
    required = True
    read_only = False


class StringField(WritableField):

    def to_python(self, value):
        if isinstance(value, six.string_types) or value is None:
            return value
        return six.u(value)


class IntegerField(WritableField):

    def to_python(self, value):
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise self.VaidationError('Invalid value. Value should be an integer.')


class FloatField(WritableField):

    def to_python(self, value):
        if value is None:
            return value
        try:
            return float(value)
        except (TypeError, ValueError):
            raise self.VaidationError('Invalid value. Value should be a float.')


class BooleanField(WritableField):

    def to_python(self, value):
        if value in (True, False):
            return bool(value)

        if value in ('t', 'True', '1'):
            return True

        if value in ('f', 'False', '0'):
            return False

        raise self.VaidationError('Invalid value. Value should be a boolean.')


class SlugField(StringField):
    regex = re.compile(r'^[-a-zA-Z0-9_]+$')

    def validate(self, value, model_instance):
        super(SlugField, self).validate(value, model_instance)
        if not bool(self.regex.search(value)):
            raise self.VaidationError('Invalid value.')
        return value


class EmailField(StringField):
    regex = re.compile(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)')

    def validate(self, value, model_instance):
        super(EmailField, self).validate(value, model_instance)

        if not value or '@' not in value:
            raise self.VaidationError('Enter a valid email address.')

        if not bool(self.regex.match(value)):
            raise self.VaidationError('Enter a valid email address.')


class ChoiceField(WritableField):

    def __init__(self, *args, **kwargs):
        self.choices = kwargs.pop('choices', [])
        self.allowed_values = [choice['value'] for choice in self.choices]
        super(ChoiceField, self).__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        super(ChoiceField, self).validate(value, model_instance)
        if self.choices and value not in self.allowed_values:
            raise self.VaidationError("Value '{0}' is not a valid choice.".format(value))


class DateField(WritableField):
    date_regex = re = re.compile(
        r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})$'
    )

    def to_python(self, value):
        if value is None:
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        try:
            parsed = self.parse_date(value)
            if parsed is not None:
                return parsed
        except ValueError:
            pass

        raise self.VaidationError("'{0}' value has an invalid date format. It must be "
                                  "in YYYY-MM-DD format.".format(value))

    def parse_date(self, value):
        match = self.date_regex.match(value)
        if match:
            kw = {k: int(v) for k, v in six.iteritems(match.groupdict())}
            return date(**kw)

    def to_native(self, value):
        if isinstance(value, datetime.datetime):
            value = value.date()
        return value.isoformat()


class DateTimeField(DateField):
    FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

    def to_python(self, value):
        if value is None:
            return value

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            value = datetime(value.year, value.month, value.day)

        value = value.split('Z')[0]

        try:
            return datetime.strptime(value, self.FORMAT)
        except ValueError:
            pass

        try:
            parsed = self.parse_date(value)
            if parsed is not None:
                return datetime(parsed.year, parsed.month, parsed.day)
        except ValueError:
            pass

        raise self.VaidationError("'{0}' value has an invalid format. It must be in "
                                  "YYYY-MM-DD HH:MM[:ss[.uuuuuu]] format.".format(value))

    def to_native(self, value):
        if value is None:
            return value
        ret = value.isoformat()
        if ret.endswith('+00:00'):
            ret = ret[:-6] + 'Z'
        return ret


class HyperlinkedField(Field):
    IGNORED_LINKS = ('self', )

    def __init__(self, *args, **kwargs):
        self.links = kwargs.pop('links', [])
        super(HyperlinkedField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(HyperlinkedField, self).contribute_to_class(cls, name)

        for link in self.links:
            name = link['name']
            endpoint = link['type']

            if name in self.IGNORED_LINKS:
                continue

            setattr(cls, name, RelatedManagerDescriptor(self, name, endpoint))


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
