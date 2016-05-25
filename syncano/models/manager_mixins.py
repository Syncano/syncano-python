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


class ArrayOperationsMixin(object):

    @clone
    def add(self, field_name, value, **kwargs):
        """
        A manager method that will add a values to the array field.

        Usage::

            data_object = Object.please.add(
                field_name='array',
                value=[10],
                class_name='arr_test',
                id=155
            )

        Consider example:

        data_object.array = [1]

        after running::

            data_object = Object.please.add(
                field_name='array',
                value=[3],
                id=data_object.id,
            )

        data_object.array will be equal: [1, 3]

        and after::

            data_object = Object.please.add(
               field_name='array',
               value=[1],
               id=data_object.id,
            )

        data_object.array will be equal: [1, 3, 1]

        :param field_name: the array field name to which elements will be added;
        :param value: the list of values to add;
        :param kwargs: class_name and id usually;
        :return: the processed data object;
        """
        self.properties.update(kwargs)
        model = self.model.get_subclass_model(**self.properties)

        self.array_validate(field_name, value, model)
        return self.array_process(field_name, value, operation_type='add')

    def remove(self, field_name, value, **kwargs):
        """
        A manager method that will remove a values from the array field.

        Usage::

            data_object = Object.please.remove(
                field_name='array',
                value=[10],
                class_name='arr_test',
                id=155
            )

        :param field_name: the array field name from which elements will be removed;
        :param value: the list of values to remove;
        :param kwargs: class_name and id usually;
        :return: the processed data object;
        """
        self.properties.update(kwargs)
        model = self.model.get_subclass_model(**self.properties)

        self.array_validate(field_name, value, model)
        return self.array_process(field_name, value, operation_type='remove')

    def add_unique(self, field_name, value, **kwargs):
        """
        A manager method that will add an unique values to the array field.

        Usage::

            data_object = Object.please.add_unique(
                field_name='array',
                value=[10],
                class_name='arr_test',
                id=155
            )

        The main distinction between add and add unique is that: add unique will not repeat elements.
        Consider example::

        data_object.array = [1]

        after running::

            data_object = Object.please.add_unique(
                field_name='array',
                value=[1],
                id=data_object.id,
            )

        data_object.array will be equal: [1]

        But if only add will be run the result will be as follow:

        data_object.array will be equal: [1, 1]

        :param field_name: field_name: the array field name to which elements will be added unique;
        :param value: the list of values to add unique;
        :param kwargs: class_name and id usually;
        :return: the processed data object;
        """
        self.properties.update(kwargs)
        model = self.model.get_subclass_model(**self.properties)

        self.array_validate(field_name, value, model)
        return self.array_process(field_name, value, operation_type='add_unique')

    @classmethod
    def array_validate(cls, field_name, value, model):

        fields = {field.name: field for field in model._meta.fields}
        if field_name not in fields:
            raise SyncanoValueError('Object has not specified field.')

        from syncano.models import ArrayField
        if not isinstance(fields[field_name], ArrayField):
            raise SyncanoValueError('Field must be of array type')

        if not isinstance(value, list):
            raise SyncanoValueError('List of values expected')

    def array_process(self, field_name, value, operation_type, **kwargs):
        self.endpoint = 'detail'
        self.method = self.get_allowed_method('PATCH', 'PUT', 'POST')
        self.data = kwargs.copy()

        if operation_type == 'add':
            array_data = {'_add': value}
        elif operation_type == 'remove':
            array_data = {'_remove': value}
        elif operation_type == 'add_unique':
            array_data = {'_addunique': value}
        else:
            raise SyncanoValueError('Operation not supported')

        self.data.update(
            {field_name: array_data}
        )

        response = self.request()
        return response
