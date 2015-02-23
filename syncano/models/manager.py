from copy import deepcopy

import six

from syncano.connection import ConnectionMixin
from syncano.exceptions import SyncanoValueError, SyncanoRequestError
from syncano.utils import get_class_name
from .registry import registry

# The maximum number of items to display in a Manager.__repr__
REPR_OUTPUT_SIZE = 20


def clone(func):
    def inner(self, *args, **kwargs):
        self = self._clone()
        return func(self, *args, **kwargs)
    return inner


class ManagerDescriptor(object):

    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, owner=None):
        if instance is not None:
            raise AttributeError("Manager isn't accessible via {0} instances.".format(owner.__name__))
        return self.manager


class RelatedManagerDescriptor(object):

    def __init__(self, field, name, endpoint):
        self.field = field
        self.name = name
        self.endpoint = endpoint

    def __get__(self, instance, owner=None):
        if instance is None:
            raise AttributeError("Manager is accessible only via {0} instances.".format(owner.__name__))

        links = getattr(instance, self.field.name)
        path = links[self.name]

        Model = registry.get_model_by_path(path)
        method = getattr(Model.please, self.endpoint, Model.please.all)

        properties = instance._meta.get_endpoint_properties('detail')
        properties = [getattr(instance, prop) for prop in properties]

        return method(*properties)


class Manager(ConnectionMixin):

    def __init__(self):
        self.name = None
        self.model = None

        self.endpoint = None
        self.properties = {}

        self.method = None
        self.query = {}
        self.data = {}

        self._limit = None
        self._serialize = True
        self._connection = None

    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = '...(remaining elements truncated)...'
        return repr(data)

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

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice,) + six.integer_types):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0)) or
                (isinstance(k, slice) and (k.start is None or k.start >= 0) and
                 (k.stop is None or k.stop >= 0))), \
            "Negative indexing is not supported."

        manager = self._clone()

        if isinstance(k, slice):
            if k.stop is not None:
                manager.limit(int(k.stop)+1)
            return list(manager)[k.start:k.stop:k.step]

        manager.limit(k+1)
        return list(manager)[k]

    # Object actions

    def create(self, **kwargs):
        attrs = kwargs.copy()
        attrs.update(self.properties)

        instance = self.model(**attrs)
        instance.save()

        return instance

    def bulk_create(self, objects):
        return [self.create(**o) for o in objects]

    @clone
    def get(self, *args, **kwargs):
        self.method = 'GET'
        self.endpoint = 'detail'
        self._filter(*args, **kwargs)
        return self.request()

    def detail(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def get_or_create(self, *args, **kwargs):
        defaults = deepcopy(kwargs.pop('defaults', {}))
        try:
            instance = self.get(*args, **kwargs)
        except self.model.DoesNotExist:
            defaults.update(kwargs)
            instance = self.create(**defaults)
        return instance

    @clone
    def delete(self, *args, **kwargs):
        self.method = 'DELETE'
        self.endpoint = 'detail'
        self._filter(*args, **kwargs)
        return self.request()

    @clone
    def update(self, *args, **kwargs):
        self.method = 'PUT'
        self.endpoint = 'detail'
        self.data = kwargs.pop('data')
        self._filter(*args, **kwargs)
        return self.request()

    def update_or_create(self, *args, **kwargs):
        data = deepcopy(kwargs.get('data', {}))
        try:
            instance = self.update(*args, **kwargs)
        except self.model.DoesNotExist:
            data.update(kwargs)
            instance = self.create(**data)
        return instance

    # List actions

    @clone
    def all(self, *args, **kwargs):
        self._limit = None
        return self.list(*args, **kwargs)

    @clone
    def list(self, *args, **kwargs):
        self.method = 'GET'
        self.endpoint = 'list'
        self._filter(*args, **kwargs)
        return self

    @clone
    def first(self, *args, **kwargs):
        try:
            self._limit = 1
            return self.list(*args, **kwargs)[0]
        except KeyError:
            return None

    @clone
    def page_size(self, value):
        if not value or not isinstance(value, six.integer_types):
            raise SyncanoValueError('page_size value needs to be an int.')

        self.query['page_size'] = value
        return self

    @clone
    def limit(self, value):
        if not value or not isinstance(value, six.integer_types):
            raise SyncanoValueError('Limit value needs to be an int.')

        self._limit = value
        return self

    @clone
    def order_by(self, field):
        if not field or not isinstance(field, six.string_types):
            raise SyncanoValueError('Order by field needs to be a string.')

        self.query['order_by'] = field
        return self

    @clone
    def raw(self):
        self._serialize = False
        return self

    @clone
    def using(self, connection):
        # ConnectionMixin will validate this
        self.connection = connection
        return self

    # Other stuff

    def contribute_to_class(self, model, name):
        setattr(model, name, ManagerDescriptor(self))

        self.model = model
        if hasattr(model._meta, 'connection') and model._meta.connection:
            self.connection = model._meta.connection

        if not self.name:
            self.name = name

    def _filter(self, *args, **kwargs):
        if args and self.endpoint:
            properties = self.model._meta.get_endpoint_properties(self.endpoint)
            mapped_args = {k: v for k, v in zip(properties, args)}
            self.properties.update(mapped_args)
        self.properties.update(kwargs)

    def _clone(self):
        # Maybe deepcopy ?
        manager = self.__class__()
        manager.name = self.name
        manager.model = self.model
        manager._connection = self._connection
        manager.endpoint = self.endpoint
        manager.properties = deepcopy(self.properties)
        manager._limit = self._limit
        manager.method = self.method
        manager.query = deepcopy(self.query)
        manager.data = deepcopy(self.data)
        manager._serialize = self._serialize

        return manager

    def serialize(self, data, model=None):
        if not isinstance(data, dict):
            return

        model = model or self.model
        properties = deepcopy(self.properties)
        properties.update(data)

        return model(**properties) if self._serialize else data

    def request(self, method=None, path=None, **request):
        meta = self.model._meta
        method = method or self.method
        path = path or meta.resolve_endpoint(self.endpoint, self.properties)

        if 'params' not in request and self.query:
            request['params'] = self.query

        if 'data' not in request and self.data:
            request['data'] = self.data

        try:
            response = self.connection.request(method, path, **request)
        except SyncanoRequestError as e:
            if e.status_code == 404:
                raise self.model.DoesNotExist
            raise

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


class WebhookManager(Manager):

    @clone
    def run(self, *args, **kwargs):
        self.method = 'GET'
        self.endpoint = 'run'
        self._filter(*args, **kwargs)
        self._serialize = False
        return self.request()


class ObjectManager(Manager):

    def create(self, **kwargs):
        attrs = kwargs.copy()
        attrs.update(self.properties)

        model = self.get_class_model(kwargs)
        instance = model(**attrs)
        instance.save()

        return instance

    def serialize(self, data):
        model = self.get_class_model(self.properties)
        return super(ObjectManager, self).serialize(data, model)

    def get_class_model(self, properties):
        instance_name = properties.get('instance_name', '')
        class_name = properties.get('class_name', '')
        model_name = get_class_name(instance_name, class_name, 'object')

        if self.model.__name__ == model_name:
            return self.model

        try:
            model = registry.get_model_by_name(model_name)
        except LookupError:
            schema = self.get_class_schema(properties)
            model = self.model.create_subclass(model_name, schema)
            registry.add(model_name, model)

        return model

    def get_class_schema(self, properties):
        instance_name = properties.get('instance_name', '')
        class_name = properties.get('class_name', '')
        parent = self.model._meta.parent
        class_ = parent.please.get(instance_name, class_name)
        return class_.schema
