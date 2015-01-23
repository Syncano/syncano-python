from copy import deepcopy

import six

from syncano.exceptions import SyncanoValueError


class ManagerDescriptor(object):

    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, type=None):
        if instance is not None:
            raise AttributeError("Manager isn't accessible via {0} instances.".format(type.__name__))
        return self.manager


class Manager(object):

    def __init__(self):
        self.name = None
        self.model = None

        self.connection = None
        self.endpoint = None
        self.endpoint_params = {}

        self.method = None
        self.query_params = {}
        self.data = {}
        self.serialize = True

    # Object actions

    def create(self, **kwargs):
        instance = self.model(**kwargs)
        instance.save()
        return instance

    def get(self):
        pass

    def detail(self):
        pass

    def delete(self):
        pass

    def update(self):
        pass

    # List actions

    def all(self):
        return self._clone()

    def list(self):
        return self._clone()

    def limit(self, value):
        if not value or not isinstance(value, six.integer_types):
            raise SyncanoValueError('Limit value needs to be an int.')

        self.query_params['limit'] = value
        return self._clone()

    def order_by(self, field):
        if not field or not isinstance(field, six.string_types):
            raise SyncanoValueError('Order by field needs to be a string.')

        self.query_params['order_by'] = field
        return self._clone()

    def raw(self, value=False):
        self.serialize = value
        return self._clone()

    # Other stuff

    def contribute_to_class(self, model, name):
        setattr(model, name, ManagerDescriptor(self))

        self.model = model
        if hasattr(model._meta, 'connection') and model._meta.connection:
            self.connection = model._meta.connection

        if not self.name:
            self.name = name

    def _clone(self, klass=None, **kwargs):
        if klass is None:
            klass = self.__class__

        manager = klass()
        manager.name = self.name
        manager.model = self.model
        manager.connection = self.connection
        manager.endpoint = self.endpoint
        manager.endpoint_params = deepcopy(self.endpoint_params)
        manager.method = self.method
        manager.query_params = deepcopy(self.query_params)
        manager.data = deepcopy(self.data)
        manager.serialize = self.serialize
        manager.__dict__.update(kwargs)

        return manager

    def request(self):
        pass
