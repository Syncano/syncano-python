# -*- coding: utf-8 -*-
from six import wraps
from syncano.exceptions import SyncanoValueError


def clone(func):
    """Decorator which will ensure that we are working on copy of ``self``.
    """
    @wraps(func)
    def inner(self, *args, **kwargs):
        self = self._clone()
        return func(self, *args, **kwargs)
    return inner


class IncrementMixin(object):

    @clone
    def increment(self, field_name, value, **kwargs):
        """
        A manager method which increments given field with given value.

        Usage::

            data_object = Object.please.increment(
                field_name='argA',
                value=10,
                class_name='testclass',
                id=1715
            )

        :param field_name: the field name to increment;
        :param value: the increment value;
        :param kwargs: class_name and id usually;
        :return: the processed (incremented) data object;
        """
        self.properties.update(kwargs)
        model = self.model.get_subclass_model(**self.properties)

        self.validate(field_name, value, model)

        return self.process(field_name, value, **kwargs)

    @clone
    def decrement(self, field_name, value, **kwargs):
        """
        A manager method which decrements given field with given value.

        Usage::

            data_object = Object.please.decrement(
                field_name='argA',
                value=10,
                class_name='testclass',
                id=1715
            )

        :param field_name: the field name to decrement;
        :param value: the decrement value;
        :param kwargs: class_name and id usually;
        :return: the processed (incremented) data object;
        """
        self.properties.update(kwargs)
        model = self.model.get_subclass_model(**self.properties)

        self.validate(field_name, value, model, operation_type='decrement')

        return self.process(field_name, value, operation_type='decrement', **kwargs)

    def process(self, field_name, value, operation_type='increment', **kwargs):
        self.endpoint = 'detail'
        self.method = self.get_allowed_method('PATCH', 'PUT', 'POST')
        self.data = kwargs.copy()

        if operation_type == 'increment':
            increment_data = {'_increment': value}
        elif operation_type == 'decrement':
            increment_data = {'_increment': -value}
        else:
            raise SyncanoValueError('Operation not supported')

        self.data.update(
            {field_name: increment_data}
        )

        response = self.request()
        return response

    @classmethod
    def validate(cls, field_name, value, model, operation_type='increment'):
        if not isinstance(value, (int, float)):
            raise SyncanoValueError('Provide an integer or float as a {} value.'.format(operation_type))

        if not value >= 0:
            raise SyncanoValueError('Value should be positive.')

        if not cls._check_field_type_for_increment(model, field_name):
            raise SyncanoValueError('{} works only on integer and float fields.'.format(operation_type.capitalize()))

    @classmethod
    def _check_field_type_for_increment(cls, model, field_name):
        fields = {}
        for field in model._meta.fields:
            fields[field.name] = field.allow_increment

        if field_name not in fields:
            raise SyncanoValueError('Object has not specified field.')

        if fields[field_name]:
            return True

        return False
