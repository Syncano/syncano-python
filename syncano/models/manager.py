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

        self._limit = None
        self.method = None
        self.query_params = {}
        self.data = {}
        self._serialize = True

    def __repr__(self):
        return self.iterator()

    def __str__(self):
        return '<Manager: {0}>'.format(self.model.__name__)

    def __unicode__(self):
        return six.u(str(self))

    def __len__(self):
        return self.iterator()

    def __iter__(self):
        return iter(self.iterator())

    def __bool__(self):
        return bool(self.iterator())

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    # Object actions

    def create(self, **kwargs):
        instance = self.model(**kwargs)
        instance.save()
        return instance

    def bulk_create(self):
        pass

    def get(self, **endpoint_params):
        self.method = 'GET'
        self.endpoint = 'detail'
        self.endpoint_params.update(endpoint_params)
        return self.request()

    def detail(self, **endpoint_params):
        return self.get(**endpoint_params)

    def get_or_create(self):
        pass

    def delete(self, **endpoint_params):
        self.method = 'DELETE'
        self.endpoint = 'detail'
        self.endpoint_params.update(endpoint_params)
        return self.request()

    def update(self, **endpoint_params):
        # TODO
        self.method = 'POST'
        self.endpoint = 'detail'
        self.data = endpoint_params.pop('data')
        self.endpoint_params.update(endpoint_params)
        return self.request()

    def update_or_create(self):
        pass

    # List actions

    def all(self, **endpoint_params):
        self._limit = None
        return self.list(**endpoint_params)

    def list(self, **endpoint_params):
        self.method = 'GET'
        self.endpoint = 'list'
        self.endpoint_params.update(endpoint_params)
        return self._clone()

    def filter(self, **endpoint_params):
        self.endpoint_params.update(endpoint_params)
        return self._clone()

    def page_size(self, value):
        if not value or not isinstance(value, six.integer_types):
            raise SyncanoValueError('page_size value needs to be an int.')

        self.query_params['page_size'] = value
        return self._clone()

    def limit(self, value):
        if not value or not isinstance(value, six.integer_types):
            raise SyncanoValueError('Limit value needs to be an int.')

        self._limit = value
        return self._clone()

    def order_by(self, field):
        if not field or not isinstance(field, six.string_types):
            raise SyncanoValueError('Order by field needs to be a string.')

        self.query_params['order_by'] = field
        return self._clone()

    def raw(self, value=False):
        self._serialize = value
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

        # Maybe deepcopy ?
        manager = klass()
        manager.name = self.name
        manager.model = self.model
        manager.connection = self.connection
        manager.endpoint = self.endpoint
        manager.endpoint_params = deepcopy(self.endpoint_params)
        manager._limit = self._limit
        manager.method = self.method
        manager.query_params = deepcopy(self.query_params)
        manager.data = deepcopy(self.data)
        manager._serialize = self._serialize
        manager.__dict__.update(kwargs)

        return manager

    def serialize(self, data):
        if not isinstance(data, dict):
            return
        return self.model(**data) if self._serialize else data

    def request(self, method=None, path=None, **request):
        meta = self.model._meta
        method = method or self.method
        path = path or meta.resolve_endpoint(self.endpoint, self.endpoint_params)

        if 'params' not in request and self.query_params:
            request['params'] = self.query_params

        if 'data' not in request and self.data:
            request['data'] = self.data

        response = self.connection.request(method, path, **request)

        if 'next' not in response:
            return self.serialize(response)

        return response

    def iterator(self):
        '''Pagination handler'''

        response = self.request()
        results = 0
        while True:
            objects = response.get('objects')
            next_url = response.get('next')

            for o in objects:
                if self._limit and results >= self._limit:
                    break

                results += 1
                yield self.serialize(o)

            if not objects or not next_url or (self._limit and results >= self._limit):
                break

            response = self.request(path=next_url)
