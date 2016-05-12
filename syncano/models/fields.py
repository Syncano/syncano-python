import json
import re
from datetime import date, datetime

import six
import validictory
from syncano import PUSH_ENV, logger
from syncano.exceptions import SyncanoFieldError, SyncanoValueError
from syncano.utils import force_text

from .geo import Distance, GeoPoint
from .manager import SchemaManager
from .registry import registry
from .relations import RelationManager, RelationValidatorMixin


class JSONToPythonMixin(object):

    def to_python(self, value):
        if value is None:
            return

        if isinstance(value, six.string_types):
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                raise SyncanoValueError('Invalid value: can not be parsed')
        return value


class Field(object):
    """Base class for all field types."""

    required = False
    read_only = True
    blank = True
    default = None
    primary_key = False

    has_data = True
    has_endpoint_data = False

    query_allowed = True
    allow_increment = False

    creation_counter = 0

    def __init__(self, name=None, **kwargs):
        self.name = name
        self.model = None
        self.default = kwargs.pop('default', self.default)
        self.required = kwargs.pop('required', self.required)
        self.read_only = kwargs.pop('read_only', self.read_only)
        self.blank = kwargs.pop('blank', self.blank)
        self.label = kwargs.pop('label', None)
        self.mapping = kwargs.pop('mapping', None)
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)
        self.query_allowed = kwargs.pop('query_allowed', self.query_allowed)
        self.has_data = kwargs.pop('has_data', self.has_data)
        self.has_endpoint_data = kwargs.pop('has_endpoint_data', self.has_endpoint_data)
        self.primary_key = kwargs.pop('primary_key', self.primary_key)

        # Adjust the appropriate creation counter, and save our local copy.
        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    def __repr__(self):
        """Displays current instance class name and field name."""
        return '<{0}: {1}>'.format(self.__class__.__name__, self.name)

    def __eq__(self, other):
        if isinstance(other, Field):
            return self.creation_counter == other.creation_counter
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Field):
            return self.creation_counter < other.creation_counter
        if isinstance(other, int):
            return self.creation_counter < other
        return NotImplemented

    def __hash__(self):  # pragma: no cover
        return hash(self.creation_counter)

    def __str__(self):
        """Wrapper around ```repr`` method."""
        return repr(self)

    def __unicode__(self):
        """Wrapper around ```repr`` method with proper encoding."""
        return six.u(repr(self))

    def __get__(self, instance, owner):
        if instance is not None:
            return instance._raw_data.get(self.name, self.default)

    def __set__(self, instance, value):
        if self.read_only and value and instance._raw_data.get(self.name):
            logger.debug('Field "{0}"" is read only, '
                         'your changes will not be saved.'.format(self.name))

        instance._raw_data[self.name] = self.to_python(value)

    def __delete__(self, instance):
        if self.name in instance._raw_data:
            del instance._raw_data[self.name]

    def validate(self, value, model_instance):
        """
        Validates the current field instance.

        :raises: SyncanoFieldError
        """
        if self.required and not value:
            raise self.ValidationError('This field is required.')

        if isinstance(value, six.string_types):
            if self.max_length and len(value) > self.max_length:
                raise self.ValidationError('Max length reached.')

            if self.min_length and len(value) < self.min_length:
                raise self.ValidationError('Min length reached.')

    def to_python(self, value):
        """
        Returns field's value prepared for usage in Python.
        """
        if isinstance(value, dict) and 'type' in value and 'value' in value:
            return value['value']

        return value

    def to_native(self, value):
        """
        Returns field's value prepared for serialization into JSON.
        """
        return value

    def to_query(self, value, lookup_type, **kwargs):
        """
        Returns field's value prepared for usage in HTTP request query.
        """
        if not self.query_allowed:
            raise self.ValidationError('Query on this field is not supported.')

        return self.to_native(value)

    def contribute_to_class(self, cls, name):
        if name in cls._meta.endpoint_fields:
            self.has_endpoint_data = True

        if not self.name:
            self.name = name

        if not self.label:
            self.label = self.name.replace('_', ' ').capitalize()

        if self.primary_key:
            if cls._meta.pk:
                raise SyncanoValueError('Multiple pk fields detected.')

            cls._meta.pk = self
            setattr(cls, 'pk', self)

        self.model = cls
        cls._meta.add_field(self)
        setattr(cls, name, self)

        error_class = type(
            '{0}ValidationError'.format(self.__class__.__name__),
            (SyncanoFieldError, ),
            {'field_name': name}
        )

        setattr(self, 'ValidationError', error_class)


class RelatedManagerField(Field):

    def __init__(self, model_name, endpoint='list', *args, **kwargs):
        super(RelatedManagerField, self).__init__(*args, **kwargs)
        self.model_name = model_name
        self.endpoint = endpoint

    def __get__(self, instance, owner=None):
        if instance is None:
            raise AttributeError("RelatedManager is accessible only via {0} instances.".format(owner.__name__))

        Model = registry.get_model_by_name(self.model_name)
        method = getattr(Model.please, self.endpoint, Model.please.all)
        properties = instance._meta.get_endpoint_properties('detail')
        properties = [getattr(instance, prop) for prop in properties]
        return method(*properties)

    def contribute_to_class(self, cls, name):
        setattr(cls, name, self)


class PrimaryKeyField(Field):
    primary_key = True


class WritableField(Field):
    required = True
    read_only = False


class EndpointField(WritableField):
    has_data = False
    has_endpoint_data = True


class StringField(WritableField):

    def to_python(self, value):
        value = super(StringField, self).to_python(value)

        if isinstance(value, six.string_types) or value is None:
            return value
        return force_text(value)


class IntegerField(WritableField):
    allow_increment = True

    def to_python(self, value):
        value = super(IntegerField, self).to_python(value)

        if value is None:
            return
        try:
            return int(value)
        except (TypeError, ValueError):
            raise self.ValidationError('Invalid value. Value should be an integer.')


class ReferenceField(IntegerField):

    def to_python(self, value):
        if isinstance(value, int):
            return value

        if hasattr(value, 'pk') and isinstance(value.pk, int):
            value = value.pk

        return super(ReferenceField, self).to_python(value)


class FloatField(WritableField):
    allow_increment = True

    def to_python(self, value):
        value = super(FloatField, self).to_python(value)

        if value is None:
            return
        try:
            return float(value)
        except (TypeError, ValueError):
            raise self.ValidationError('Invalid value. Value should be a float.')


class BooleanField(WritableField):

    def to_python(self, value):
        value = super(BooleanField, self).to_python(value)

        if value is None:
            return

        if value in (True, 't', 'true', 'True', '1'):
            return True

        if value in (False, 'f', 'false', 'False', '0'):
            return False

        raise self.ValidationError('Invalid value. Value should be a boolean.')


class SlugField(StringField):
    regex = re.compile(r'^[-a-zA-Z0-9_]+$')

    def validate(self, value, model_instance):
        super(SlugField, self).validate(value, model_instance)

        if not isinstance(value, six.string_types):
            raise self.ValidationError('Invalid value. Value should be a string.')

        if not bool(self.regex.search(value)):
            raise self.ValidationError('Invalid value.')
        return value


class EmailField(StringField):
    regex = re.compile(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)')

    def validate(self, value, model_instance):
        super(EmailField, self).validate(value, model_instance)

        if not isinstance(value, six.string_types):
            raise self.ValidationError('Invalid value. Value should be a string.')

        if not value or '@' not in value:
            raise self.ValidationError('Enter a valid email address.')

        if not bool(self.regex.match(value)):
            raise self.ValidationError('Enter a valid email address.')


class ChoiceField(WritableField):

    def __init__(self, *args, **kwargs):
        self.choices = kwargs.pop('choices', [])
        self.allowed_values = [choice['value'] for choice in self.choices]
        super(ChoiceField, self).__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        super(ChoiceField, self).validate(value, model_instance)
        if self.choices and value is not None and value not in self.allowed_values:
            raise self.ValidationError("Value '{0}' is not a valid choice.".format(value))


class DateField(WritableField):
    date_regex = re = re.compile(
        r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})$'
    )

    def to_python(self, value):
        value = super(DateField, self).to_python(value)

        if value is None:
            return

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value)
            return dt.date()

        try:
            parsed = self.parse_date(value)
            if parsed is not None:
                return parsed
        except (ValueError, TypeError):
            pass

        raise self.ValidationError("'{0}' value has an invalid date format. It must be "
                                   "in YYYY-MM-DD format.".format(value))

    def parse_date(self, value):
        match = self.date_regex.match(value)
        if match:
            kw = {k: int(v) for k, v in six.iteritems(match.groupdict())}
            return date(**kw)

    def to_native(self, value):
        if isinstance(value, datetime):
            value = value.date()
        return value.isoformat()


class DateTimeField(DateField):
    FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

    def to_python(self, value):
        if value is None:
            return

        if isinstance(value, dict) and 'type' in value and 'value' in value:
            value = value['value']

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)

        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)

        if isinstance(value, six.string_types):
            value = value.split('Z')[0]

        parsers = [
            self.parse_from_string,
            self.parse_from_date,
        ]

        for parser in parsers:
            try:
                value = parser(value)
            except (ValueError, TypeError):
                pass
            else:
                return value

        raise self.ValidationError("'{0}' value has an invalid format. It must be in "
                                   "YYYY-MM-DD HH:MM[:ss[.uuuuuu]] format.".format(value))

    def parse_from_string(self, value):
        return datetime.strptime(value, self.FORMAT)

    def parse_from_date(self, value):
        parsed = self.parse_date(value)

        if not parsed:
            raise ValueError

        return datetime(parsed.year, parsed.month, parsed.day)

    def to_native(self, value):
        if value is None:
            return
        ret = value.strftime(self.FORMAT)
        if ret.endswith('+00:00'):
            ret = ret[:-6] + 'Z'

        if not ret.endswith('Z'):
            ret = ret + 'Z'

        return ret


class LinksWrapper(object):

    def __init__(self, links_dict, ignored_links):
        self.links_dict = links_dict
        self.ignored_links = ignored_links

    def __getattribute__(self, item):
        try:
            return super(LinksWrapper, self).__getattribute__(item)
        except AttributeError:
            value = self.links_dict.get(item)
            if not value:
                item = item.replace('_', '-')
                value = self.links_dict.get(item)

            if not value:
                raise

            return value

    def to_native(self):
        return self.links_dict


class LinksField(Field):
    query_allowed = False
    IGNORED_LINKS = ('self', )

    def __init__(self, *args, **kwargs):
        super(LinksField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        return LinksWrapper(value, self.IGNORED_LINKS)

    def to_native(self, value):
        return value


class ModelField(Field):

    def __init__(self, rel, *args, **kwargs):
        self.rel = rel
        self.just_pk = kwargs.pop('just_pk', True)
        super(ModelField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(ModelField, self).contribute_to_class(cls, name)

        if isinstance(self.rel, six.string_types):

            def lazy_relation(cls, field):
                if isinstance(field.rel, six.string_types):
                    field.rel = registry.get_model_by_name(field.rel)

            try:
                self.rel = registry.get_model_by_name(self.rel)
            except LookupError:
                value = (lazy_relation, (cls, self), {})
                registry._pending_lookups.setdefault(self.rel, []).append(value)
            else:
                lazy_relation(cls, self)

    def validate(self, value, model_instance):
        super(ModelField, self).validate(value, model_instance)

        if not isinstance(value, (self.rel, dict)):
            raise self.ValidationError('Value needs to be a {0} instance.'.format(self.rel.__name__))

        if self.required and isinstance(value, self.rel):
            value.validate()

    def to_python(self, value):

        if value is None:
            return

        if isinstance(value, self.rel):
            return value

        if isinstance(value, dict):
            return self.rel(**value)

        raise self.ValidationError("'{0}' has unsupported format.".format(value))

    def to_native(self, value):
        if value is None:
            return

        if isinstance(value, self.rel):
            if not self.just_pk:
                return value.to_native()

            pk_field = value._meta.pk
            pk_value = getattr(value, pk_field.name)
            return pk_field.to_native(pk_value)

        return value


class FileField(WritableField):
    param_name = 'files'

    def to_native(self, value):
        return {self.name: value}


class JSONField(JSONToPythonMixin, WritableField):
    query_allowed = False
    schema = None

    def __init__(self, *args, **kwargs):
        self.schema = kwargs.pop('schema', None) or self.schema
        super(JSONField, self).__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        super(JSONField, self).validate(value, model_instance)
        if self.schema:
            try:
                validictory.validate(value, self.schema)
            except ValueError as e:
                raise self.ValidationError(e)

    def to_native(self, value):
        if value is None:
            return

        if not isinstance(value, six.string_types):
            value = json.dumps(value)
        return value


class ArrayField(JSONToPythonMixin, WritableField):

    def validate(self, value, model_instance):
        super(ArrayField, self).validate(value, model_instance)

        if not self.required and not value:
            return

        if isinstance(value, six.string_types):
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                raise SyncanoValueError('Expected an array')

        if not isinstance(value, list):
            raise SyncanoValueError('Expected an array')

        for element in value:
            if not isinstance(element, six.string_types + (bool, int, float)):
                raise SyncanoValueError(
                    'Currently supported types for array items are: string types, bool, float and int')


class ObjectField(JSONToPythonMixin, WritableField):

    def validate(self, value, model_instance):
        super(ObjectField, self).validate(value, model_instance)

        if not self.required and not value:
            return

        if isinstance(value, six.string_types):
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                raise SyncanoValueError('Expected an object')

        if not isinstance(value, dict):
            raise SyncanoValueError('Expected an object')


class SchemaField(JSONField):
    required = False
    query_allowed = False
    not_indexable_types = ['text', 'file']
    schema = {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'name': {
                    'type': 'string',
                    'required': True,
                },
                'type': {
                    'type': 'string',
                    'required': True,
                    'enum': [
                        'string',
                        'text',
                        'integer',
                        'float',
                        'boolean',
                        'datetime',
                        'file',
                        'reference',
                        'relation',
                        'array',
                        'object',
                        'geopoint',
                    ],
                },
                'order_index': {
                    'type': 'boolean',
                    'required': False,
                },
                'filter_index': {
                    'type': 'boolean',
                    'required': False,
                },
                'target': {
                    'type': 'string',
                    'required': False,
                }
            }
        }
    }

    def validate(self, value, model_instance):
        if value is None:
            return

        if isinstance(value, SchemaManager):
            value = value.schema

        super(SchemaField, self).validate(value, model_instance)

        fields = [f['name'] for f in value]
        if len(fields) != len(set(fields)):
            raise self.ValidationError('Field names must be unique.')

        for field in value:
            is_not_indexable = field['type'] in self.not_indexable_types
            has_index = ('order_index' in field or 'filter_index' in field)
            if is_not_indexable and has_index:
                raise self.ValidationError('"{0}" type is not indexable.'.format(field['type']))

    def to_python(self, value):
        if isinstance(value, SchemaManager):
            return value

        value = super(SchemaField, self).to_python(value)
        return SchemaManager(value)

    def to_native(self, value):
        if isinstance(value, SchemaManager):
            value = value.schema

        return super(SchemaField, self).to_native(value)


class PushJSONField(JSONField):
    def to_native(self, value):
        if value is None:
            return

        if not isinstance(value, six.string_types):
            if 'environment' not in value:
                value.update({
                    'environment': PUSH_ENV,
                })
            value = json.dumps(value)
        return value


class GeoPointField(Field):

    def validate(self, value, model_instance):
        super(GeoPointField, self).validate(value, model_instance)

        if not self.required and not value:
            return

        if isinstance(value, six.string_types):
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                raise SyncanoValueError('Expected an object')

        if not isinstance(value, GeoPoint):
            raise SyncanoValueError('Expected a GeoPoint')

    def to_native(self, value):
        if value is None:
            return

        if isinstance(value, bool):
            return value  # exists lookup

        if isinstance(value, dict):
            value = GeoPoint(latitude=value['latitude'], longitude=value['longitude'])

        if isinstance(value, tuple):
            geo_struct = value[0].to_native()
        else:
            geo_struct = value.to_native()

        geo_struct = json.dumps(geo_struct)

        return geo_struct

    def to_query(self, value, lookup_type, **kwargs):
        """
        Returns field's value prepared for usage in HTTP request query.
        """
        super(GeoPointField, self).to_query(value, lookup_type, **kwargs)

        if lookup_type not in ['near', 'exists']:
            raise SyncanoValueError('Lookup {} not supported for geopoint field'.format(lookup_type))

        if lookup_type in ['exists']:
            if isinstance(value, bool):
                return value
            else:
                raise SyncanoValueError('Bool expected in {} lookup.'.format(lookup_type))

        if isinstance(value, dict):
            value = (
                GeoPoint(latitude=value.pop('latitude'), longitude=value.pop('longitude')),
                Distance(**value)
            )

        if len(value) != 2 or not isinstance(value[0], GeoPoint) or not isinstance(value[1], Distance):
            raise SyncanoValueError('This lookup should be a tuple with GeoPoint and Distance: '
                                    '<field_name>__near=(GeoPoint(52.12, 22.12), Distance(kilometers=100))')

        query_dict = value[0].to_native()
        query_dict.update(value[1].to_native())

        return query_dict

    def to_python(self, value):
        if value is None:
            return

        value = self._process_string_types(value)

        if isinstance(value, GeoPoint):
            return value

        latitude, longitude = self._process_value(value)

        if not latitude or not longitude:
            raise SyncanoValueError('Expected the `longitude` and `latitude` fields.')

        return GeoPoint(latitude=latitude, longitude=longitude)

    @classmethod
    def _process_string_types(cls, value):
        if isinstance(value, six.string_types):
            try:
                return json.loads(value)
            except (ValueError, TypeError):
                raise SyncanoValueError('Invalid value: can not be parsed.')
        return value

    @classmethod
    def _process_value(cls, value):
        longitude = None
        latitude = None

        if isinstance(value, dict):
            latitude = value.get('latitude')
            longitude = value.get('longitude')
        elif isinstance(value, (tuple, list)):
            try:
                latitude = value[0]
                longitude = value[1]
            except IndexError:
                raise SyncanoValueError('Can not parse the geo point.')

        return latitude, longitude


class RelationField(RelationValidatorMixin, WritableField):
    query_allowed = True

    def __call__(self, instance, field_name):
        return RelationManager(instance=instance, field_name=field_name)

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, dict) and 'type' in value and 'value' in value:
            value = value['value']

        if isinstance(value, dict) and ('_add' in value or '_remove' in value):
            return value

        if not isinstance(value, (list, tuple)):
            return [value]

        return value

    def to_query(self, value, lookup_type, related_field_name=None, related_field_lookup=None, **kwargs):

        if not self.query_allowed:
            raise self.ValidationError('Query on this field is not supported.')

        if lookup_type not in ['contains', 'is']:
            raise SyncanoValueError('Lookup {} not supported for relation field.'.format(lookup_type))

        query_dict = {}

        if lookup_type == 'contains':
            if self._check_relation_value(value):
                value = [obj.id for obj in value]
            query_dict = value

        if lookup_type == 'is':
            query_dict = {related_field_name: {"_{0}".format(related_field_lookup): value}}

        return query_dict

    def to_native(self, value):
        if not value:
            return None

        if isinstance(value, dict) and ('_add' in value or '_remove' in value):
            return value

        if not isinstance(value, (list, tuple)):
            value = [value]

        if self._check_relation_value(value):
            value = [obj.id for obj in value]
        return value


MAPPING = {
    'string': StringField,
    'text': StringField,
    'file': FileField,
    'ref': StringField,
    'reference': ReferenceField,
    'relation': RelationField,
    'integer': IntegerField,
    'float': FloatField,
    'boolean': BooleanField,
    'name': SlugField,
    'email': EmailField,
    'choice': ChoiceField,
    'date': DateField,
    'datetime': DateTimeField,
    'field': Field,
    'writable': WritableField,
    'endpoint': EndpointField,
    'links': LinksField,
    'model': ModelField,
    'json': JSONField,
    'schema': SchemaField,
    'array': ArrayField,
    'object': ObjectField,
    'geopoint': GeoPointField,
}
