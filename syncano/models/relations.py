# -*- coding: utf-8 -*-
from syncano.exceptions import SyncanoValueError


class RelationValidatorMixin(object):

    def validate(self, value, model_instance):
        super(RelationValidatorMixin, self).validate(value, model_instance)
        self._validate(value)

    @classmethod
    def _validate(cls, value):
        value = cls._make_list(value)
        all_ints = all([isinstance(x, int) for x in value])
        from .archetypes import Model
        all_objects = all([isinstance(obj, Model) for obj in value])
        object_types = [type(obj) for obj in value]
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
        if self._validate(args):
            value_ids = [obj.id for obj in args]
        else:
            value_ids = args

        connection = self.instance._meta.connection

        data = {self.field_name: {'_add': value_ids}}
        meta = self.instance._meta
        update_path = meta.get_endpoint(name='detail')['path']
        update_path = update_path.format(**self.instance.get_endpoint_data())
        response = connection.request('PATCH', update_path, data=data)
        self.instance.to_python(response)

    def remove(self, *args):
        if self._validate(args):
            value_ids = [obj.id for obj in args]
        else:
            value_ids = args

        connection = self.instance._meta.connection

        data = {self.field_name: {'_remove': value_ids}}
        meta = self.instance._meta
        update_path = meta.get_endpoint(name='detail')['path']
        update_path = update_path.format(**self.instance.get_endpoint_data())
        response = connection.request('PATCH', update_path, data=data)
        self.instance.to_python(response)
