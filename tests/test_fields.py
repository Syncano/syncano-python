import json
import unittest
from datetime import datetime
from functools import wraps
from time import mktime

import six
from syncano import models
from syncano.exceptions import SyncanoValidationError, SyncanoValueError
from syncano.models.manager import SchemaManager


def skip_base_class(func):

    @wraps(func)
    def inner(self, *args, **kwargs):
        f = func
        if not self.field_name:
            f = unittest.skip('Skipping base class method')(f)
        return f(self, *args, **kwargs)
    return inner


class AllFieldsModel(models.Model):
    CHOICES = (
        {'display_name': 'test_one', 'value': 1},
        {'display_name': 'test_two', 'value': 2},
    )

    SCHEMA = {
        'properties': {
            'results': {
                'items': [
                    {'type': 'integer'},
                    {'type': 'string'},
                    {'type': 'boolean'},
                    {'type': 'null'},
                    {'type': 'number'}
                ]
            }
        }
    }

    base_field = models.Field()
    default_base_field = models.Field(default=10)
    read_only_base_field = models.Field(read_only=True)

    primary_key_field = models.PrimaryKeyField()
    writable_field = models.WritableField()
    endpoint_field = models.EndpointField()
    string_field = models.StringField()
    integer_field = models.IntegerField()
    float_field = models.FloatField()
    boolean_field = models.BooleanField()
    slug_field = models.SlugField()
    email_field = models.EmailField()
    choice_field = models.ChoiceField(choices=CHOICES)
    date_field = models.DateField()
    datetime_field = models.DateTimeField()
    hyperlinked_field = models.LinksField()
    model_field = models.ModelField('Instance')
    json_field = models.JSONField(schema=SCHEMA)
    schema_field = models.SchemaField()
    array_field = models.ArrayField()
    object_field = models.ObjectField()
    geo_field = models.GeoPointField()

    class Meta:
        endpoints = {
            'detail': {
                'methods': ['delete', 'post', 'patch', 'get'],
                'path': '/v1.1/dummy/{dynamic_field}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/v1.1/dummy/',
            }
        }


class BaseTestCase(unittest.TestCase):
    field_name = None

    def setUp(self):
        self.model = AllFieldsModel
        self.fields = self.model._meta.fields
        self.instance = self.model()
        self.field = None

        if self.field_name:
            self.field = self.instance._meta.get_field(self.field_name)

    @skip_base_class
    def test_field_repr(self):
        expected = '<{0}: {1}>'.format(
            self.field.__class__.__name__,
            self.field_name
        )
        out = repr(self.field)
        self.assertEqual(out, expected)

    @skip_base_class
    def test_field_str(self):
        expected = '<{0}: {1}>'.format(
            self.field.__class__.__name__,
            self.field_name
        )
        out = str(self.field)
        self.assertEqual(out, expected)

    @skip_base_class
    def test_field_unicode(self):
        expected = six.u('<{0}: {1}>').format(
            self.field.__class__.__name__,
            self.field_name
        )
        out = str(self.field)
        self.assertEqual(out, expected)

    @skip_base_class
    def test_field_name(self):
        self.assertTrue(self.field.name)

    @skip_base_class
    def test_field_label(self):
        self.assertTrue(self.field.label)

    @skip_base_class
    def test_field_model(self):
        self.assertEqual(self.field.model, self.model)

    @skip_base_class
    def test_field_error_class(self):
        self.assertTrue(hasattr(self.field, 'ValidationError'))
        self.assertTrue(issubclass(self.field.ValidationError, SyncanoValidationError))
        self.assertEqual(self.field.ValidationError.field_name, self.field.name)


class FieldTestCase(BaseTestCase):
    field_name = 'base_field'

    def test_fields_creation_counter_order(self):
        counter = 0
        for field in self.fields:
            self.assertTrue(field.creation_counter > counter)
            counter = field.creation_counter

    def test_eq_comparison(self):
        string_field = self.instance._meta.get_field('string_field')
        integer_field = self.instance._meta.get_field('integer_field')
        self.assertFalse(string_field == integer_field)
        self.assertFalse(string_field == 4)

    def test_lt_comparison(self):
        string_field = self.instance._meta.get_field('string_field')
        integer_field = self.instance._meta.get_field('integer_field')
        self.assertFalse(integer_field < string_field)
        self.assertFalse(integer_field < 4)

    def test_get(self):
        self.assertTrue(self.field_name not in self.instance._raw_data)
        self.instance._raw_data[self.field_name] = 1
        self.assertEqual(getattr(self.instance, self.field_name), 1)

    def test_default_value(self):
        self.assertTrue('default_base_field' not in self.instance._raw_data)
        self.assertEqual(getattr(self.instance, 'default_base_field'), 10)
        self.assertTrue('default_base_field' not in self.instance._raw_data)

    def test_set(self):
        self.assertTrue(self.field_name not in self.instance._raw_data)
        self.instance.base_field = 10
        self.assertTrue(self.field_name in self.instance._raw_data)
        self.assertEqual(getattr(self.instance, self.field_name), 10)
        self.assertEqual(self.instance._raw_data[self.field_name], 10)

    def test_set_read_only_value(self):
        self.assertTrue('read_only_base_field' not in self.instance._raw_data)
        self.instance.read_only_base_field = 10
        self.assertTrue('read_only_base_field' in self.instance._raw_data)
        self.assertEqual(self.instance.read_only_base_field, 10)
        self.instance.read_only_base_field = 12
        self.assertEqual(self.instance.read_only_base_field, 12)

    def test_delete(self):
        self.assertTrue(self.field_name not in self.instance._raw_data)
        self.instance.base_field = 10
        self.assertTrue(self.field_name in self.instance._raw_data)
        del self.instance.base_field
        self.assertTrue(self.field_name not in self.instance._raw_data)

    def test_required_validation(self):
        self.field.required = True
        with self.assertRaises(SyncanoValidationError):
            self.field.validate(None, self.instance)

    def test_min_length_validation(self):
        self.field.required = True
        self.field.min_length = 10
        with self.assertRaises(SyncanoValidationError):
            self.field.validate('a', self.instance)

    def test_max_length_validation(self):
        self.field.required = True
        self.field.max_length = 2
        with self.assertRaises(SyncanoValidationError):
            self.field.validate('aaa', self.instance)

    def test_successful_validation(self):
        self.field.required = True
        self.field.min_length = 2
        self.field.max_length = 10
        self.field.validate('aaa', self.instance)

    def test_to_python(self):
        result = self.field.to_python(1)
        self.assertEqual(result, 1)

    def test_to_native(self):
        result = self.field.to_native(1)
        self.assertEqual(result, 1)

    def test_to_query(self):
        result = self.field.to_query(1, None)
        self.assertEqual(result, 1)

        self.field.query_allowed = False
        with self.assertRaises(SyncanoValueError):
            self.field.to_query(1, None)


class PrimaryKeyTestCase(BaseTestCase):
    field_name = 'primary_key_field'

    def test_multiple_pk_fields(self):
        with self.assertRaises(SyncanoValueError):
            class MultiplePkModel(models.Model):
                pk_one = models.PrimaryKeyField()
                pk_two = models.PrimaryKeyField()


class WritableFieldTestCase(BaseTestCase):
    field_name = 'writable_field'


class EndpointFieldTestCase(BaseTestCase):
    field_name = 'endpoint_field'


class StringFieldTestCase(BaseTestCase):
    field_name = 'string_field'

    def test_to_python(self):
        self.assertEqual(self.field.to_python(None), None)
        self.assertEqual(self.field.to_python('test'), 'test')
        self.assertEqual(self.field.to_python(10), '10')
        self.assertEqual(self.field.to_python(10.0), '10.0')
        self.assertEqual(self.field.to_python(True), 'True')
        self.assertEqual(self.field.to_python({'a': 1}), "{'a': 1}")
        self.assertEqual(self.field.to_python([1, 2]), "[1, 2]")


class IntegerFieldTestCase(BaseTestCase):
    field_name = 'integer_field'

    def test_to_python(self):
        self.assertEqual(self.field.to_python(None), None)
        self.assertEqual(self.field.to_python(10), 10)
        self.assertEqual(self.field.to_python(10.5), 10)

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python('test')

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python({'a': 2})


class FloatFieldTestCase(BaseTestCase):
    field_name = 'float_field'

    def test_to_python(self):
        self.assertEqual(self.field.to_python(None), None)
        self.assertEqual(self.field.to_python(10), 10.0)
        self.assertEqual(self.field.to_python(10.5), 10.5)

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python('test')

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python({'a': 2})


class BooleanFieldTestCase(BaseTestCase):
    field_name = 'boolean_field'

    def test_to_python(self):
        self.assertEqual(self.field.to_python(True), True)
        self.assertEqual(self.field.to_python('True'), True)
        self.assertEqual(self.field.to_python('1'), True)
        self.assertEqual(self.field.to_python('t'), True)

        self.assertEqual(self.field.to_python(False), False)
        self.assertEqual(self.field.to_python('False'), False)
        self.assertEqual(self.field.to_python('0'), False)
        self.assertEqual(self.field.to_python('f'), False)

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python('test')

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python({'a': 2})


class SlugFieldTestCase(BaseTestCase):
    field_name = 'slug_field'

    def test_successful_validation(self):
        self.field.validate('fine-slug', self.instance)

    def test_validation_failure(self):
        with self.assertRaises(SyncanoValidationError):
            self.field.validate('test dsfd', self.instance)

        with self.assertRaises(SyncanoValidationError):
            self.field.validate('!*&()', self.instance)

        with self.assertRaises(SyncanoValidationError):
            self.field.validate({'a': 1}, self.instance)


class EmailFieldTestCase(BaseTestCase):
    field_name = 'email_field'

    def test_successful_validation(self):
        self.field.validate('dummy@email.com', self.instance)

    def test_validation_failure(self):
        with self.assertRaises(SyncanoValidationError):
            self.field.validate(None, self.instance)

        with self.assertRaises(SyncanoValidationError):
            self.field.validate('!*&()', self.instance)

        with self.assertRaises(SyncanoValidationError):
            self.field.validate('almost@email', self.instance)

        with self.assertRaises(SyncanoValidationError):
            self.field.validate({'a': 1}, self.instance)


class ChoiceFieldTestCase(BaseTestCase):
    field_name = 'choice_field'

    def test_successful_validation(self):
        self.field.validate(1, self.instance)
        self.field.validate(2, self.instance)

    def test_validation_failure(self):
        with self.assertRaises(SyncanoValidationError):
            self.field.validate(None, self.instance)

        with self.assertRaises(SyncanoValidationError):
            self.field.validate(3, self.instance)


class DateFieldTestCase(BaseTestCase):
    field_name = 'date_field'

    def test_to_python(self):
        now = datetime.now()
        date = now.date()
        timestamp = mktime(now.timetuple())

        self.assertEqual(self.field.to_python(None), None)
        self.assertEqual(self.field.to_python(now), date)
        self.assertEqual(self.field.to_python(date), date)
        self.assertEqual(self.field.to_python(timestamp), date)
        self.assertEqual(self.field.to_python(date.strftime('%Y-%m-%d')), date)

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python('not-a-date')

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python({'a': 1})

    def test_to_native(self):
        now = datetime.now()
        date = now.date()
        result = date.isoformat()
        self.assertEqual(self.field.to_native(now), result)
        self.assertEqual(self.field.to_native(date), result)


class DatetimeFieldTestCase(BaseTestCase):
    field_name = 'datetime_field'

    def test_to_python(self):
        now = datetime.now()
        date = now.date()
        date_result = datetime(date.year, date.month, date.day)
        timestamp = mktime(now.timetuple())

        self.assertEqual(self.field.to_python(None), None)
        self.assertEqual(self.field.to_python(now), now)
        self.assertEqual(self.field.to_python(date), date_result)
        self.assertEqual(self.field.to_python(timestamp), now.replace(microsecond=0))
        self.assertEqual(self.field.to_python(now.strftime(self.field.FORMAT)), now)
        self.assertEqual(self.field.to_python(date.strftime('%Y-%m-%d')), date_result)

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python('not-a-datetime')

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python({'a': 1})

    def test_to_native(self):
        now = datetime.now()
        self.assertEqual(self.field.to_native(None), None)
        self.assertEqual(self.field.to_native(now), '%sZ' % now.isoformat())


class HyperlinkedFieldTestCase(BaseTestCase):
    field_name = 'hyperlinked_field'


class ModelFieldTestCase(BaseTestCase):
    field_name = 'model_field'

    def test_successful_validation(self):
        value = models.Instance(name='test', description='tests')
        self.field.validate(value, self.instance)

        self.field.required = True
        self.field.validate(value, self.instance)

    def test_validation_failure(self):
        with self.assertRaises(SyncanoValidationError):
            self.field.validate(1, self.instance)

    def test_to_python(self):
        kwargs = {'name': 'test', 'description': 'tests'}
        value = models.Instance(**kwargs)

        self.assertEqual(self.field.to_python(None), None)
        self.assertEqual(self.field.to_python(kwargs), value)
        self.assertEqual(self.field.to_python(value), value)

        with self.assertRaises(SyncanoValidationError):
            self.field.to_python('not-a-datetime')

    def test_to_native(self):
        kwargs = {'name': 'test', 'description': 'tests'}
        value = models.Instance(**kwargs)

        self.assertEqual(self.field.to_native(None), None)
        self.assertEqual(self.field.to_native(kwargs), kwargs)
        self.assertEqual(self.field.to_native(value), value.pk)

        self.field.just_pk = False
        self.assertEqual(self.field.to_native(value), value.to_native())


class JSONFieldTestCase(BaseTestCase):
    field_name = 'json_field'

    def test_successful_validation(self):
        value = {'results': [1, 'a', False, None, 5.3]}
        self.field.validate(value, self.instance)

    def test_validation_failure(self):
        value = {'results': [1, 2, 3, 4]}
        with self.assertRaises(SyncanoValidationError):
            self.field.validate(value, self.instance)

    def test_to_python(self):
        self.assertEqual(self.field.to_python(None), None)
        self.assertEqual(self.field.to_python({'a': 1}), {'a': 1})
        self.assertEqual(self.field.to_python('{"a": 1}'), {'a': 1})

    def test_to_native(self):
        self.assertEqual(self.field.to_native(None), None)
        self.assertEqual(self.field.to_native({'a': 1}), '{"a": 1}')
        self.assertEqual(self.field.to_native('{"a": 1}'), '{"a": 1}')


class SchemaFieldTestCase(BaseTestCase):
    field_name = 'schema_field'

    def test_successful_validation(self):
        value = [
            {'name': 'username', 'type': 'string'},
            {'name': 'result', 'type': 'integer'},
        ]
        self.field.validate(value, self.instance)
        self.field.validate(SchemaManager(value), self.instance)

    def test_unique_names_validation(self):
        value = [
            {'name': 'username', 'type': 'string'},
            {'name': 'username', 'type': 'integer'},
        ]

        with self.assertRaises(SyncanoValidationError):
            self.field.validate(value, self.instance)

    def test_index_validation(self):
        value = [
            {'name': 'result', 'type': 'string'},
            {'name': 'username', 'type': 'text', 'order_index': True},
        ]

        with self.assertRaises(SyncanoValidationError):
            self.field.validate(value, self.instance)

    def test_to_python(self):
        value = [
            {'name': 'username', 'type': 'string'},
            {'name': 'result', 'type': 'integer'},
        ]

        schema = SchemaManager(value)

        self.assertEqual(self.field.to_python(None), SchemaManager())
        self.assertEqual(self.field.to_python(value), schema)
        self.assertEqual(self.field.to_python(schema), schema)

    def test_to_native(self):
        value = [{'name': 'username', 'type': 'string'}]

        schema = SchemaManager(value)
        self.assertEqual(self.field.to_native(None), None)
        self.assertListEqual(json.loads(self.field.to_native(schema)), [{"type": "string", "name": "username"}])
        self.assertListEqual(json.loads(self.field.to_native(value)), [{"type": "string", "name": "username"}])


class ArrayFieldTestCase(BaseTestCase):
    field_name = 'array_field'

    def test_validate(self):

        with self.assertRaises(SyncanoValueError):
            self.field.validate("a", self.instance)

        with self.assertRaises(SyncanoValueError):
            self.field.validate([1, 2, [12, 13]], self.instance)

        self.field.validate([1, 2, 3], self.instance)
        self.field.validate("[1, 2, 3]", self.instance)

    def test_to_python(self):
        with self.assertRaises(SyncanoValueError):
            self.field.to_python('a')

        self.field.to_python([1, 2, 3, 4])
        self.field.to_python("[1, 2, 3, 4]")


class ObjectFieldTestCase(BaseTestCase):
    field_name = 'object_field'

    def test_validate(self):

        with self.assertRaises(SyncanoValueError):
            self.field.validate("a", self.instance)

        self.field.validate({'raz': 1, 'dwa': 2}, self.instance)
        self.field.validate('{"raz": 1, "dwa": 2}', self.instance)

    def test_to_python(self):
        with self.assertRaises(SyncanoValueError):
            self.field.to_python('a')

        self.field.to_python({'raz': 1, 'dwa': 2})
        self.field.to_python('{"raz": 1, "dwa": 2}')


class GeoPointTestCase(BaseTestCase):
    field_name = 'geo_field'

    def test_validate(self):

        with self.assertRaises(SyncanoValueError):
            self.field.validate(12, self.instance)

        self.field.validate(models.GeoPoint(latitude=52.12, longitude=12.02), self.instance)

    def test_to_python(self):
        with self.assertRaises(SyncanoValueError):
            self.field.to_python(12)

        self.field.to_python((52.12, 12.02))
        self.field.to_python({'latitude': 52.12, 'longitude': 12.02})
