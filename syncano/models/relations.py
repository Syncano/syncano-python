# -*- coding: utf-8 -*-
from syncano.exceptions import SyncanoValueError


class RelationValidatorMixin(object):

    def validate(self, value, model_instance):
        super(RelationValidatorMixin, self).validate(value, model_instance)
        self._check_relation_value(value)

    @classmethod
    def _check_relation_value(cls, value):
        if value is None:
            return False

        if '_add' in value or '_remove' in value:
            check_value = value.get('_add') or value.get('_remove')
        else:
            check_value = value

        check_value = cls._make_list(check_value)

        all_ints = all([isinstance(x, int) for x in check_value])
        from .archetypes import Model
        all_objects = all([isinstance(obj, Model) for obj in check_value])
        object_types = [type(obj) for obj in check_value]
        if len(set(object_types)) != 1:
            raise SyncanoValueError("All objects should be the same type.")

        if (all_ints and all_objects) or (not all_ints and not all_objects):
            raise SyncanoValueError("List elements should be objects or integers.")

        if all_objects:
            return True
        return False

    @classmethod
    def _make_list(cls, value):
        if not isinstance(value, (list, tuple)):
            value = [value]
        return value


class RelationManager(RelationValidatorMixin):

    def __init__(self, instance, field_name):
        super(RelationManager, self).__init__()
        self.instance = instance
        self.model = instance._meta
        self.field_name = field_name

    def add(self, *args):
        self._add_or_remove(args)

    def remove(self, *args):
        self._add_or_remove(args, operation='_remove')

    def _add_or_remove(self, id_list, operation='_add'):
        if self._check_relation_value(id_list):
            value_ids = [obj.id for obj in id_list]
        else:
            value_ids = id_list

        meta = self.instance._meta
        connection = meta.connection

        data = {self.field_name: {operation: value_ids}}
        update_path = meta.get_endpoint(name='detail')['path']
        update_path = update_path.format(**self.instance.get_endpoint_data())
        response = connection.request('PATCH', update_path, data=data)
        self.instance.to_python(response)
