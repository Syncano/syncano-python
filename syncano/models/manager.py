import json
from copy import deepcopy

import six
from syncano.connection import ConnectionMixin
from syncano.exceptions import SyncanoRequestError, SyncanoValidationError, SyncanoValueError
from syncano.models.bulk import ModelBulkCreate, ObjectBulkCreate
from syncano.models.manager_mixins import IncrementMixin, clone

from .registry import registry

# The maximum number of items to display in a Manager.__repr__
REPR_OUTPUT_SIZE = 20


class ManagerDescriptor(object):

    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, owner=None):
        if instance is not None:
            raise AttributeError("Manager isn't accessible via {0} instances.".format(owner.__name__))
        return self.manager.all()


class Manager(ConnectionMixin):
    """Base class responsible for all ORM (``please``) actions."""

    BATCH_URI = '/v1.1/instances/{name}/batch/'

    def __init__(self):
        self.name = None
        self.model = None

        self.endpoint = None
        self.properties = {}

        self.method = None
        self.query = {}
        self.data = {}
        self.is_lazy = False
        self._filter_kwargs = {}

        self._limit = None
        self._serialize = True
        self._connection = None
        self._template = None

    def __repr__(self):  # pragma: no cover
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = '...(remaining elements truncated)...'
        return repr(data)

    def __str__(self):  # pragma: no cover
        return '<Manager: {0}>'.format(self.model.__name__)

    def __unicode__(self):  # pragma: no cover
        return six.u(str(self))

    def __len__(self):  # pragma: no cover
        return self.iterator()

    def __iter__(self):  # pragma: no cover
        return iter(self.iterator())

    def __nonzero__(self):
        try:
            self[0]
            return True
        except IndexError:
            return False

    def __bool__(self):  # pragma: no cover
        try:
            self[0]
            return True
        except IndexError:
            return False

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
                manager.limit(int(k.stop) + 1)
            return list(manager)[k.start:k.stop:k.step]

        manager.limit(k + 1)
        return list(manager)[k]

    def _set_default_properties(self, endpoint_properties):
        for field in self.model._meta.fields:

            is_demanded = field.name in endpoint_properties
            has_default = field.default is not None

            if is_demanded and has_default:
                self.properties[field.name] = field.default

    def as_batch(self):
        self.is_lazy = True
        return self

    def batch(self, *args):
        """
        A convenience method for making a batch request. Only create, update and delete manager method are supported.
        Batch request are limited to 50. So the args length should be equal or less than 50.

        Usage::

            klass = instance.classes.get(name='some_class')
            Object.please.batch(
                klass.objects.as_batch().delete(id=652),
                klass.objects.as_batch().delete(id=653),
                ...
            )

        and::

            Object.please.batch(
                klass.objects.as_batch().update(id=652, arg='some_b'),
                klass.objects.as_batch().update(id=653, arg='some_b'),
                ...
            )

        and::

            Object.please.batch(
                klass.objects.as_batch().create(arg='some_c'),
                klass.objects.as_batch().create(arg='some_c'),
                ...
            )

        and::

            Object.please.batch(
                klass.objects.as_batch().delete(id=653),
                klass.objects.as_batch().update(id=652, arg='some_a'),
                klass.objects.as_batch().create(arg='some_c'),
                ...
            )

        are posible.

        But::

            Object.please.batch(
                klass.objects.as_batch().get_or_create(id=653, arg='some_a')
            )

        will not work as expected.

        Some snippet for working with instance users::

            instance = Instance.please.get(name='Nabuchodonozor')
            model_users = instance.users.batch(
                instance.users.as_batch().delete(id=7),
                instance.users.as_batch().update(id=9, username='username_a'),
                instance.users.as_batch().create(username='username_b', password='5432'),
                ...
            )

        And sample response will be::

            [{u'code': 204}, <User: 9>, <User: 11>, ...]

        :param args: a arg is on of the: klass.objects.as_batch().create(...), klass.objects.as_batch().update(...),
         klass.objects.as_batch().delete(...)
        :return: a list with objects corresponding to batch arguments; update and create will return a populated Object,
         when delete return a raw response from server (usually a dict: {'code': 204}, sometimes information about not
         found resource to delete);
        """
        # firstly turn off lazy mode:
        self.is_lazy = False

        meta = []
        requests = []
        for arg in args:
            if isinstance(arg, list):  # update now can return a list;
                for nested_arg in arg:
                    meta.append(nested_arg['meta'])
                    requests.append(nested_arg['body'])
            else:
                meta.append(arg['meta'])
                requests.append(arg['body'])

        response = self.connection.request(
            'POST',
            self.BATCH_URI.format(name=registry.instance_name),
            **{'data': {'requests': requests}}
        )

        populated_response = []

        for meta, res in zip(meta, response):
            if res['code'] in [200, 201]:  # success response: update or create;
                content = res['content']
                model = meta['model']
                properties = meta['properties']
                content.update(properties)
                populated_response.append(model(**content))
            else:
                populated_response.append(res)

        return populated_response

    # Object actions
    def create(self, **kwargs):
        """
        A convenience method for creating an object and saving it all in one step. Thus::

            instance = Instance.please.create(name='test-one', description='description')

        and::

            instance = Instance(name='test-one', description='description')
            instance.save()

        are equivalent.
        """
        data = self.properties.copy()
        attrs = kwargs.copy()
        data.update(attrs)
        data.update({'is_lazy': self.is_lazy})
        instance = self._get_instance(data)

        if instance.__class__.__name__ == 'Instance':
            registry.set_used_instance(instance.name)

        saved_instance = instance.save()
        if not self.is_lazy:
            return instance

        return saved_instance

    def bulk_create(self, *objects):
        """
        Creates many new instances based on provided list of objects.

        Usage::

            instance = Instance.please.get(name='instance_a')
            instances = instance.users.bulk_create(
                User(username='user_a', password='1234'),
                User(username='user_b', password='4321')
            )

        Warning::

            This method is restricted to handle 50 objects at once.
        """
        return ModelBulkCreate(objects, self).process()

    @clone
    def get(self, *args, **kwargs):
        """
        Returns the object matching the given lookup parameters.

        Usage::

            instance = Instance.please.get('test-one')
            instance = Instance.please.get(name='test-one')
        """
        self.method = 'GET'
        self.endpoint = 'detail'
        self._filter(*args, **kwargs)
        return self.request()

    @clone
    def in_bulk(self, object_ids_list, **kwargs):
        """
        A method which allows to bulk get objects;

        Use::

            response = Classes.please.in_bulk(['test_class', ...])

        response is:

            > {'test_class': <Class: test_class>}

        For objects:

            res = Object.please.in_bulk([1, 2], class_name='test_class')

        or

            res = klass.objects.in_bulk([1, 2])

        response is:

            {1: <SyncanoTestClassObject: 1>, 2: {u'content': {u'detail': u'Not found.'}, u'code': 404}}


        :param object_ids_list: This list expects the primary keys - id in api, a names, ids can be used here;
        :return: a dict in which keys are the object_ids_list elements, and values are a populated objects;
        """
        self.properties.update(kwargs)
        path, defaults = self._get_endpoint_properties()
        requests = [
            {'method': 'GET', 'path': '{path}{id}/'.format(path=path, id=object_id)} for object_id in object_ids_list
        ]

        response = self.connection.request(
            'POST',
            self.BATCH_URI.format(name=registry.instance_name),
            **{'data': {'requests': requests}}
        )

        bulk_response = {}

        for object_id, object in zip(object_ids_list, response):
            if object['code'] == 200:
                data = object['content'].copy()
                data.update(self.properties)
                bulk_response[object_id] = self.model(**data)
            else:
                bulk_response[object_id] = object

        return bulk_response

    def detail(self, *args, **kwargs):
        """
        Wrapper around ``get`` method.

        Usage::

            instance = Instance.please.detail('test-one')
            instance = Instance.please.detail(name='test-one')
        """
        return self.get(*args, **kwargs)

    def get_or_create(self, **kwargs):
        """
        A convenience method for looking up an object with the given
        lookup parameters, creating one if necessary.

        Returns a tuple of **(object, created)**, where **object** is the retrieved or
        **created** object and created is a boolean specifying whether a new object was created.

        This is meant as a shortcut to boilerplatish code. For example::

            try:
                instance = Instance.please.get(name='test-one')
            except Instance.DoesNotExist:
                instance = Instance(name='test-one', description='test')
                instance.save()

        The above example can be rewritten using **get_or_create()** like so::

            instance, created = Instance.please.get_or_create(name='test-one', defaults={'description': 'test'})
        """
        defaults = deepcopy(kwargs.pop('defaults', {}))
        try:
            instance = self.get(**kwargs)
        except self.model.DoesNotExist:
            defaults.update(kwargs)
            instance = self.create(**defaults)
            created = True
        else:
            created = False
        return instance, created

    @clone
    def delete(self, *args, **kwargs):
        """
        Removes single instance based on provided arguments.
        Returns None if deletion went fine.

        Usage::

            Instance.please.delete('test-one')
            Instance.please.delete(name='test-one')
        """
        self.method = 'DELETE'
        self.endpoint = 'detail'
        self._filter(*args, **kwargs)
        if not self.is_lazy:
            return self.request()

        path, defaults = self._get_endpoint_properties()

        return self.model.batch_object(method=self.method, path=path, body=self.data, properties=defaults)

    @clone
    def filter(self, **kwargs):
        endpoint_fields = [field.name for field in self.model._meta.fields if field.has_endpoint_data]
        for kwarg_name in kwargs:
            if kwarg_name not in endpoint_fields:
                raise SyncanoValueError('Only endpoint properties can be used in filter: {}'.format(endpoint_fields))
        self._filter_kwargs = kwargs
        return self

    @clone
    def update(self, *args, **kwargs):
        if self._filter_kwargs or self.query:  # means that .filter() was run;
            return self.new_update(**kwargs)
        return self.old_update(*args, **kwargs)

    @clone
    def new_update(self, **kwargs):
        """
        Updates multiple instances based on provided arguments. There to ways to do so:

            1. Django-style update.
            2. By specifying arguments.

        Usage::

            objects = Object.please.list(instance_name=INSTANCE_NAME,
                                 class_name='someclass').filter(id=1).update(arg='103')
            objects = Object.please.list(instance_name=INSTANCE_NAME,
                                 class_name='someclass').filter(id=1).update(arg='103')

        The return value is a list of objects;

        """

        model_fields = [field.name for field in self.model._meta.fields if not field.has_endpoint_data]
        for field_name in kwargs:
            if field_name not in model_fields:
                raise SyncanoValueError('This model has not field {}'.format(field_name))

        self.endpoint = 'detail'
        self.method = self.get_allowed_method('PATCH', 'PUT', 'POST')
        self.data = kwargs.copy()

        if self._filter_kwargs:  # Manager context;
            # do a single object update: Class, Instance for example;
            self.data.update(self._filter_kwargs)
            serialized = self._get_serialized_data()
            self._filter(*(), **self.data)  # sets the proper self.properties here

            if not self.is_lazy:
                return [self.serialize(self.request(), self.model)]

            path, defaults = self._get_endpoint_properties()
            return [self.model.batch_object(method=self.method, path=path, body=serialized, properties=defaults)]

        instances = []  # ObjectManager context;
        for obj in self:
            self._filter(*(), **kwargs)
            serialized = self._get_serialized_data()
            self.properties.update({'id': obj.id})
            path, defaults = self._get_endpoint_properties()
            updated_instance = self.model.batch_object(method=self.method, path=path, body=serialized,
                                                       properties=defaults)

        instances.append(updated_instance)  # always a batch structure here;

        if not self.is_lazy:
            instances = self.batch(instances)

        return instances

    @clone
    def old_update(self, *args, **kwargs):
        """
        Updates single instance based on provided arguments. There to ways to do so:

            1. Django-style update.
            2. By specifying **data** argument.

        The **data** is a dictionary of (field, value) pairs used to update the object.

        Usage::

            instance = Instance.please.update('test-one', description='new one')
            instance = Instance.please.update(name='test-one', description='new one')

            instance = Instance.please.update('test-one', data={'description': 'new one'})
            instance = Instance.please.update(name='test-one', data={'description': 'new one'})
        """
        self.endpoint = 'detail'
        self.method = self.get_allowed_method('PATCH', 'PUT', 'POST')
        data = kwargs.pop('data', {})
        self.data = kwargs.copy()
        self.data.update(data)

        model = self.serialize(self.data, self.model)

        serialized = model.to_native()

        serialized = {k: v for k, v in six.iteritems(serialized)
                      if k in self.data}

        self.data.update(serialized)
        self._filter(*args, **kwargs)

        if not self.is_lazy:
            return self.request()

        path, defaults = self._get_endpoint_properties()
        return self.model.batch_object(method=self.method, path=path, body=self.data, properties=defaults)

    def update_or_create(self, defaults=None, **kwargs):
        """
        A convenience method for updating an object with the given parameters, creating a new one if necessary.
        The ``defaults`` is a dictionary of (field, value) pairs used to update the object.

        Returns a tuple of **(object, created)**, where object is the created or updated object and created
        is a boolean specifying whether a new object was created.

        The **update_or_create** method tries to fetch an object from Syncano API based on the given kwargs.
        If a match is found, it updates the fields passed in the defaults dictionary.

        This is meant as a shortcut to boilerplatish code. For example::

            try:
                instance = Instance.please.update(name='test-one', data=updated_values)
            except Instance.DoesNotExist:
                updated_values.update({'name': 'test-one'})
                instance = Instance(**updated_values)
                instance.save()

        This pattern gets quite unwieldy as the number of fields in a model goes up.
        The above example can be rewritten using **update_or_create()** like so::

            instance, created = Instance.please.update_or_create(name='test-one',
                                                                 defaults=updated_values)
        """
        defaults = deepcopy(defaults or {})
        try:
            instance = self.update(**kwargs)
        except self.model.DoesNotExist:
            defaults.update(kwargs)
            instance = self.create(**defaults)
            created = True
        else:
            created = False
        return instance, created

    # List actions

    @clone
    def all(self, *args, **kwargs):
        """
        Returns a copy of the current ``Manager`` with limit removed.

        Usage::

            instances = Instance.please.all()
        """
        self._limit = None
        return self.list(*args, **kwargs)

    @clone
    def list(self, *args, **kwargs):
        """
        Returns a copy of the current ``Manager`` containing objects that match the given lookup parameters.

        Usage::
            instance = Instance.please.list()
            classes = Class.please.list(instance_name='test-one')
        """
        self.method = 'GET'
        self.endpoint = 'list'
        self._filter(*args, **kwargs)
        return self

    @clone
    def first(self, *args, **kwargs):
        """
        Returns the first object matched by the lookup parameters or None, if there is no matching object.

        Usage::

            instance = Instance.please.first()
            classes = Class.please.first(instance_name='test-one')
        """
        try:
            self._limit = 1
            return self.list(*args, **kwargs)[0]
        except KeyError:
            return None

    @clone
    def page_size(self, value):
        """
        Sets page size.

        Usage::

            instances = Instance.please.page_size(20).all()
        """
        if not value or not isinstance(value, six.integer_types):
            raise SyncanoValueError('page_size value needs to be an int.')

        self.query['page_size'] = value
        return self

    @clone
    def limit(self, value):
        """
        Sets limit of returned objects.

        Usage::

            instances = Instance.please.list().limit(10)
            classes = Class.please.list(instance_name='test-one').limit(10)
        """
        if not value or not isinstance(value, six.integer_types):
            raise SyncanoValueError('Limit value needs to be an int.')

        self._limit = value
        return self

    @clone
    def ordering(self, order='asc'):
        """
        Sets order of returned objects.

        Usage::

            instances = Instance.please.ordering()
        """
        if order not in ('asc', 'desc'):
            raise SyncanoValueError('Invalid order value.')

        self.query['ordering'] = order
        return self

    @clone
    def raw(self):
        """
        Disables serialization. ``request`` method will return raw Python types.

        Usage::

            >>> instances = Instance.please.list().raw()
            >>> instances
            [{'description': 'new one', 'name': 'test-one'...}...]
        """
        self._serialize = False
        return self

    @clone
    def template(self, name):
        """
        Disables serialization. ``request`` method will return raw text.

        Usage::

            >>> instances = Instance.please.list().template('test')
            >>> instances
            u'text'
        """
        self._serialize = False
        self._template = name
        return self

    @clone
    def using(self, connection):
        """
        Connection juggling.
        """
        # ConnectionMixin will validate this
        self.connection = connection
        return self

    # Other stuff

    def contribute_to_class(self, model, name):  # pragma: no cover
        setattr(model, name, ManagerDescriptor(self))

        self.model = model

        if not self.name:
            self.name = name

    def _get_serialized_data(self):
        model = self.serialize(self.data, self.model)
        serialized = model.to_native()
        serialized = {k: v for k, v in six.iteritems(serialized)
                      if k in self.data}
        self.data.update(serialized)
        return serialized

    def _filter(self, *args, **kwargs):
        properties = self.model._meta.get_endpoint_properties(self.endpoint)

        self._set_default_properties(properties)

        if args and self.endpoint:
            # let user get object by 'id'
            too_much_properties = len(args) < len(properties)
            id_specified = 'id' in properties

            if too_much_properties and id_specified:
                properties = ['id']

            mapped_args = {k: v for k, v in zip(properties, args)}
            self.properties.update(mapped_args)
        self.properties.update(kwargs)

    def _clone(self):
        # Maybe deepcopy ?
        manager = self.__class__()
        manager.name = self.name
        manager.model = self.model
        manager._connection = self._connection
        manager._template = self._template
        manager.endpoint = self.endpoint
        manager.properties = deepcopy(self.properties)
        manager._limit = self._limit
        manager.method = self.method
        manager.query = deepcopy(self.query)
        manager._filter_kwargs = deepcopy(self._filter_kwargs)
        manager.data = deepcopy(self.data)
        manager._serialize = self._serialize
        manager.is_lazy = self.is_lazy

        return manager

    def serialize(self, data, model=None):
        """Serializes passed data to related :class:`~syncano.models.base.Model` class."""
        model = model or self.model
        if data == '':
            return

        if isinstance(data, model):
            return data

        if not isinstance(data, dict):
            raise SyncanoValueError('Unsupported data type.')

        properties = deepcopy(self.properties)
        properties.update(data)
        return model(**properties) if self._serialize else data

    def build_request(self, request):
        if 'params' not in request and self.query:
            request['params'] = self.query

        if 'data' not in request and self.data:
            request['data'] = self.data

        if 'headers' not in request:
            request['headers'] = {}

        if self._template is not None and 'X-TEMPLATE-RESPONSE' not in request['headers']:
            request['headers']['X-TEMPLATE-RESPONSE'] = self._template

    def request(self, method=None, path=None, **request):
        """Internal method, which calls Syncano API and returns serialized data."""
        meta = self.model._meta
        method = method or self.method
        allowed_methods = meta.get_endpoint_methods(self.endpoint)

        if not path:
            path, defaults = self._get_endpoint_properties()

        if method.lower() not in allowed_methods:
            methods = ', '.join(allowed_methods)
            raise SyncanoValueError('Unsupported request method "{0}" allowed are {1}.'.format(method, methods))

        self.build_request(request)

        try:
            response = self.connection.request(method, path, **request)
        except SyncanoRequestError as e:
            if e.status_code == 404:
                obj_id = path.rsplit('/')[-2]
                raise self.model.DoesNotExist("{} not found.".format(obj_id))
            raise

        if 'next' not in response and not self._template:
            return self.serialize(response)

        return response

    def get_allowed_method(self, *methods):
        meta = self.model._meta
        allowed_methods = meta.get_endpoint_methods(self.endpoint)

        for method in methods:
            if method.lower() in allowed_methods:
                return method

        methods = ', '.join(methods)
        raise SyncanoValueError('Unsupported request methods {0}.'.format(methods))

    def iterator(self):
        """Pagination handler"""

        response = self._get_response()
        results = 0
        while True:
            if self._template:
                yield response
                break
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

    def _get_response(self):
        return self.request()

    def _get_instance(self, attrs):
        return self.model(**attrs)

    def _get_endpoint_properties(self):
        defaults = {f.name: f.default for f in self.model._meta.fields if f.default is not None}
        defaults.update(self.properties)
        return self.model._meta.resolve_endpoint(self.endpoint, defaults), defaults


class ScriptManager(Manager):
    """
    Custom :class:`~syncano.models.manager.Manager`
    class for :class:`~syncano.models.base.Script` model.
    """

    @clone
    def run(self, *args, **kwargs):
        payload = kwargs.pop('payload', {})

        if not isinstance(payload, six.string_types):
            payload = json.dumps(payload)

        self.method = 'POST'
        self.endpoint = 'run'
        self.data['payload'] = payload
        self._filter(*args, **kwargs)
        self._serialize = False
        response = self.request()
        return registry.ScriptTrace(**response)


class ScriptEndpointManager(Manager):
    """
    Custom :class:`~syncano.models.manager.Manager`
    class for :class:`~syncano.models.base.ScriptEndpoint` model.
    """

    @clone
    def run(self, *args, **kwargs):
        payload = kwargs.pop('payload', {})

        if not isinstance(payload, six.string_types):
            payload = json.dumps(payload)

        self.method = 'POST'
        self.endpoint = 'run'
        self.data['payload'] = payload
        self._filter(*args, **kwargs)
        self._serialize = False
        response = self.request()

        # Workaround for circular import
        return registry.ScriptEndpointTrace(**response)


class ObjectManager(IncrementMixin, Manager):
    """
    Custom :class:`~syncano.models.manager.Manager`
    class for :class:`~syncano.models.base.Object` model.
    """
    LOOKUP_SEPARATOR = '__'
    ALLOWED_LOOKUPS = [
        'gt', 'gte', 'lt', 'lte',
        'eq', 'neq', 'exists', 'in', 'startswith',
        'near', 'is', 'contains',
    ]

    def __init__(self):
        super(ObjectManager, self).__init__()
        self._initial_response = None

    def serialize(self, data, model=None):
        model = model or self.model.get_subclass_model(**self.properties)
        return super(ObjectManager, self).serialize(data, model)

    @clone
    def count(self):
        """
        Return the queryset count;

        Usage::

            Object.please.list(instance_name='raptor', class_name='some_class').filter(id__gt=600).count()
            Object.please.list(instance_name='raptor', class_name='some_class').count()
            Object.please.all(instance_name='raptor', class_name='some_class').count()

        :return: The count of the returned objects: count = DataObjects.please.list(...).count();
        """
        self.method = 'GET'
        self.query.update({
            'include_count': True,
            'page_size': 0,
        })
        response = self.request()
        return response['objects_count']

    @clone
    def with_count(self, page_size=20):
        """
        Return the queryset with count;

        Usage::

            Object.please.list(instance_name='raptor', class_name='some_class').filter(id__gt=600).with_count()
            Object.please.list(instance_name='raptor', class_name='some_class').with_count(page_size=30)
            Object.please.all(instance_name='raptor', class_name='some_class').with_count()

        :param page_size: The size of the pagination; Default to 20;
        :return: The tuple with objects and the count: objects, count = DataObjects.please.list(...).with_count();
        """
        query_data = {
            'include_count': True,
            'page_size': page_size,
        }

        self.method = 'GET'
        self.query.update(query_data)
        response = self.request()
        self._initial_response = response
        return self, self._initial_response['objects_count']

    @clone
    def filter(self, **kwargs):
        """
        Special method just for data object :class:`~syncano.models.base.Object` model.

        Usage::

            objects = Object.please.list('instance-name', 'class-name').filter(henryk__gte='hello')
        """
        query = {}
        model = self.model.get_subclass_model(**self.properties)

        for field_name, value in six.iteritems(kwargs):
            lookup = 'eq'
            model_name = None

            if self.LOOKUP_SEPARATOR in field_name:
                model_name, field_name, lookup = self._get_lookup_attributes(field_name)

            for field in model._meta.fields:
                if field.name == field_name:
                    break

            self._validate_lookup(model, model_name, field_name, lookup, field)

            query_main_lookup, query_main_field = self._get_main_lookup(model_name, field_name, lookup)

            query.setdefault(query_main_field, {})
            query[query_main_field]['_{0}'.format(query_main_lookup)] = field.to_query(
                value,
                query_main_lookup,
                related_field_name=field_name,
                related_field_lookup=lookup,
            )

        self.query['query'] = json.dumps(query)
        self.method = 'GET'
        self.endpoint = 'list'
        return self

    def _get_lookup_attributes(self, field_name):
        try:
            model_name, field_name, lookup = field_name.split(self.LOOKUP_SEPARATOR, 2)
        except ValueError:
            model_name = None
            field_name, lookup = field_name.split(self.LOOKUP_SEPARATOR, 1)

        return model_name, field_name, lookup

    def _validate_lookup(self, model, model_name, field_name, lookup, field):
        if not model_name and field_name not in model._meta.field_names:
            allowed = ', '.join(model._meta.field_names)
            raise SyncanoValueError('Invalid field name "{0}" allowed are {1}.'.format(field_name, allowed))

        if lookup not in self.ALLOWED_LOOKUPS:
            allowed = ', '.join(self.ALLOWED_LOOKUPS)
            raise SyncanoValueError('Invalid lookup type "{0}" allowed are {1}.'.format(lookup, allowed))

        if model_name and field.__class__.__name__ != 'RelationField':
            raise SyncanoValueError('Lookup supported only for RelationField.')

    @classmethod
    def _get_main_lookup(cls, model_name, field_name, lookup):
        if model_name:
            return 'is', model_name
        else:
            return lookup, field_name

    def bulk_create(self, *objects):
        """
        Creates many new objects.
        Usage::

            created_objects = Object.please.bulk_create(
                Object(instance_name='instance_a', class_name='some_class', title='one'),
                Object(instance_name='instance_a', class_name='some_class', title='two'),
                Object(instance_name='instance_a', class_name='some_class', title='three')
            )

        :param objects: a list of the instances of data objects to be created;
        :return: a created and populated list of objects; When error occurs a plain dict is returned in that place;
        """
        return ObjectBulkCreate(objects, self).process()

    def _get_response(self):
        return self._initial_response or self.request()

    def _get_instance(self, attrs):
        return self.model.get_subclass_model(**attrs)(**attrs)

    def _get_model_field_names(self):
        object_fields = [f.name for f in self.model._meta.fields]
        schema = self.model.get_class_schema(**self.properties)

        return object_fields + [i['name'] for i in schema.schema]

    def _validate_fields(self, model_fields, args):
        for arg in args:
            if arg not in model_fields:
                msg = 'Field "{0}" does not exist in class {1}.'
                raise SyncanoValidationError(
                    msg.format(arg, self.properties['class_name']))

    @clone
    def fields(self, *args):
        """
        Special method just for data object :class:`~syncano.models.base.Object` model.

        Usage::

            objects = Object.please.list('instance-name', 'class-name').fields('name', 'id')
        """
        model_fields = self._get_model_field_names()
        self._validate_fields(model_fields, args)
        self.query['fields'] = ','.join(args)
        self.method = 'GET'
        self.endpoint = 'list'
        return self

    @clone
    def exclude(self, *args):
        """
        Special method just for data object :class:`~syncano.models.base.Object` model.

        Usage::

            objects = Object.please.list('instance-name', 'class-name').exclude('avatar')
        """
        model_fields = self._get_model_field_names()
        self._validate_fields(model_fields, args)

        fields = [f for f in model_fields if f not in args]

        self.query['fields'] = ','.join(fields)
        self.method = 'GET'
        self.endpoint = 'list'
        return self

    def ordering(self, order=None):
        raise AttributeError('Ordering not implemented. Use order_by instead.')

    @clone
    def order_by(self, field):
        """
        Sets ordering field of returned objects.

        Usage::

            # ASC order
            instances = Object.please.order_by('name')

            # DESC order
            instances = Object.please.order_by('-name')
        """
        if not field or not isinstance(field, six.string_types):
            raise SyncanoValueError('Order by field needs to be a string.')

        self.query['order_by'] = field
        return self

    def _clone(self):
        manager = super(ObjectManager, self)._clone()
        manager._initial_response = self._initial_response
        return manager


class SchemaManager(object):
    """
    Custom :class:`~syncano.models.manager.Manager`
    class for :class:`~syncano.models.fields.SchemaFiled`.
    """

    def __init__(self, schema=None):
        self.schema = schema or []

    def __eq__(self, other):
        if isinstance(other, SchemaManager):
            return self.schema == other.schema
        return NotImplemented

    def __str__(self):  # pragma: no cover
        return str(self.schema)

    def __repr__(self):  # pragma: no cover
        return '<SchemaManager>'

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.schema[key]

        if isinstance(key, six.string_types):
            for v in self.schema:
                if v['name'] == key:
                    return v

        raise KeyError

    def __setitem__(self, key, value):
        value = deepcopy(value)
        value['name'] = key
        self.remove(key)
        self.add(value)

    def __delitem__(self, key):
        self.remove(key)

    def __iter__(self):
        return iter(self.schema)

    def __contains__(self, item):
        if not self.schema:
            return False
        return item in self.schema

    def set(self, value):
        """Sets schema value."""
        self.schema = value

    def add(self, *objects):
        """Adds multiple objects to schema."""
        self.schema.extend(objects)

    def remove(self, *names):
        """Removes selected objects based on their names."""
        values = [v for v in self.schema if v['name'] not in names]
        self.set(values)

    def clear(self):
        """Sets empty schema."""
        self.set([])

    def set_index(self, field, order=False, filter=False):
        """Sets index on selected field.

        :type field: string
        :param field: Name of schema field

        :type filter: bool
        :param filter: Sets filter index on selected field

        :type order: bool
        :param order: Sets order index on selected field
        """
        if not order and not filter:
            raise ValueError('Choose at least one index.')

        if order:
            self[field]['order_index'] = True

        if filter:
            self[field]['filter_index'] = True

    def set_order_index(self, field):
        """Shortcut for ``set_index(field, order=True)``."""
        self.set_index(field, order=True)

    def set_filter_index(self, field):
        """Shortcut for ``set_index(field, filter=True)``."""
        self.set_index(field, filter=True)

    def remove_index(self, field, order=False, filter=False):
        """Removes index from selected field.

        :type field: string
        :param field: Name of schema field

        :type filter: bool
        :param filter: Removes filter index from selected field

        :type order: bool
        :param order: Removes order index from selected field
        """
        if not order and not filter:
            raise ValueError('Choose at least one index.')

        if order and 'order_index' in self[field]:
            del self[field]['order_index']

        if filter and 'filter_index' in self[field]:
            del self[field]['filter_index']

    def remove_order_index(self, field):
        """Shortcut for ``remove_index(field, order=True)``."""
        self.remove_index(field, order=True)

    def remove_filter_index(self, field):
        """Shortcut for ``remove_index(field, filter=True)``."""
        self.remove_index(field, filter=True)
