

from copy import deepcopy

from syncano.exceptions import SyncanoValidationError
from syncano.utils import get_class_name

from . import fields
from .base import Model
from .instances import Instance
from .manager import ObjectManager
from .registry import registry


class Class(Model):
    """
    OO wrapper around instance classes `link <http://docs.syncano.com/docs/classes>`_.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar description: :class:`~syncano.models.fields.StringField`
    :ivar objects_count: :class:`~syncano.models.fields.Field`
    :ivar schema: :class:`~syncano.models.fields.SchemaField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar status: :class:`~syncano.models.fields.Field`
    :ivar metadata: :class:`~syncano.models.fields.JSONField`
    :ivar revision: :class:`~syncano.models.fields.IntegerField`
    :ivar expected_revision: :class:`~syncano.models.fields.IntegerField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar group: :class:`~syncano.models.fields.IntegerField`
    :ivar group_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar other_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar objects: :class:`~syncano.models.fields.RelatedManagerField`

    .. note::
        This model is special because each related :class:`~syncano.models.base.Object` will be
        **dynamically populated** with fields defined in schema attribute.
    """

    PERMISSIONS_CHOICES = (
        {'display_name': 'None', 'value': 'none'},
        {'display_name': 'Read', 'value': 'read'},
        {'display_name': 'Create objects', 'value': 'create_objects'},
    )

    name = fields.StringField(max_length=64, primary_key=True)
    description = fields.StringField(read_only=False, required=False)
    objects_count = fields.Field(read_only=True, required=False)

    schema = fields.SchemaField(read_only=False)
    links = fields.LinksField()
    status = fields.Field()
    metadata = fields.JSONField(read_only=False, required=False)

    revision = fields.IntegerField(read_only=True, required=False)
    expected_revision = fields.IntegerField(read_only=False, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)

    group = fields.IntegerField(label='group id', required=False)
    group_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')
    other_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, default='none')

    objects = fields.RelatedManagerField('Object')

    class Meta:
        parent = Instance
        plural_name = 'Classes'
        endpoints = {
            'detail': {
                'methods': ['get', 'put', 'patch', 'delete'],
                'path': '/classes/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/classes/',
            }
        }

    def save(self, **kwargs):
        if self.schema:  # do not allow add empty schema to registry;
            registry.set_schema(self.name, self.schema.schema)  # update the registry schema here;
        return super(Class, self).save(**kwargs)


class Object(Model):
    """
    OO wrapper around data objects `link <http://docs.syncano.com/docs/data-objects>`_.

    :ivar revision: :class:`~syncano.models.fields.IntegerField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar owner: :class:`~syncano.models.fields.IntegerField`
    :ivar owner_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar group: :class:`~syncano.models.fields.IntegerField`
    :ivar group_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar other_permissions: :class:`~syncano.models.fields.ChoiceField`
    :ivar channel: :class:`~syncano.models.fields.StringField`
    :ivar channel_room: :class:`~syncano.models.fields.StringField`

    .. note::
        This model is special because each instance will be **dynamically populated**
        with fields defined in related :class:`~syncano.models.base.Class` schema attribute.
    """

    PERMISSIONS_CHOICES = (
        {'display_name': 'None', 'value': 'none'},
        {'display_name': 'Read', 'value': 'read'},
        {'display_name': 'Write', 'value': 'write'},
        {'display_name': 'Full', 'value': 'full'},
    )

    revision = fields.IntegerField(read_only=True, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    owner = fields.IntegerField(label='owner id', required=False)
    owner_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, required=False)
    group = fields.IntegerField(label='group id', required=False)
    group_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, required=False)
    other_permissions = fields.ChoiceField(choices=PERMISSIONS_CHOICES, required=False)
    channel = fields.StringField(required=False)
    channel_room = fields.StringField(required=False, max_length=64)

    please = ObjectManager()

    class Meta:
        parent = Class
        endpoints = {
            'detail': {
                'methods': ['delete', 'post', 'patch', 'get'],
                'path': '/objects/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/objects/',
            }
        }

    @staticmethod
    def __new__(cls, **kwargs):
        instance_name = cls._get_instance_name(kwargs)
        class_name = cls._get_class_name(kwargs)
        if not instance_name:
            raise SyncanoValidationError('Field "instance_name" is required.')

        if not class_name:
            raise SyncanoValidationError('Field "class_name" is required.')

        model = cls.get_subclass_model(instance_name, class_name)
        return model(**kwargs)

    @classmethod
    def _set_up_object_class(cls, model):
        pass

    @classmethod
    def _get_instance_name(cls, kwargs):
        return kwargs.get('instance_name')

    @classmethod
    def _get_class_name(cls, kwargs):
        return kwargs.get('class_name')

    @classmethod
    def create_subclass(cls, name, schema):
        meta = deepcopy(Object._meta)
        attrs = {
            'Meta': meta,
            '__new__': Model.__new__,  # We don't want to have maximum recursion depth exceeded error
            'please': ObjectManager()
        }

        model = type(str(name), (Model, ), attrs)

        for field in schema:
            field_type = field.get('type')
            field_class = fields.MAPPING[field_type]
            query_allowed = ('order_index' in field or 'filter_index' in field)
            field_class(required=False, read_only=False, query_allowed=query_allowed).contribute_to_class(
                model, field.get('name')
            )

        for field in meta.fields:
            if field.primary_key:
                setattr(model, 'pk', field)
            setattr(model, field.name, field)

        cls._set_up_object_class(model)
        return model

    @classmethod
    def get_or_create_subclass(cls, name, schema):
        try:
            subclass = registry.get_model_by_name(name)
        except LookupError:
            subclass = cls.create_subclass(name, schema)
            registry.add(name, subclass)
        return subclass

    @classmethod
    def get_subclass_name(cls, instance_name, class_name):
        return get_class_name(instance_name, class_name, 'object')

    @classmethod
    def get_class_schema(cls, instance_name, class_name):
        schema = registry.get_schema(class_name)
        if not schema:
            parent = cls._meta.parent
            schema = parent.please.get(instance_name, class_name).schema
            if schema:  # do not allow to add to registry empty schema;
                registry.set_schema(class_name, schema)
        return schema

    @classmethod
    def get_subclass_model(cls, instance_name, class_name, **kwargs):
        """
        Creates custom :class:`~syncano.models.base.Object` sub-class definition based
        on passed **instance_name** and **class_name**.
        """
        model_name = cls.get_subclass_name(instance_name, class_name)

        if cls.__name__ == model_name:
            return cls

        try:
            model = registry.get_model_by_name(model_name)
        except LookupError:
            parent = cls._meta.parent
            schema = parent.please.get(instance_name, class_name).schema
            model = cls.create_subclass(model_name, schema)
            registry.add(model_name, model)

        schema = cls.get_class_schema(instance_name, class_name)

        for field in schema:
            try:
                getattr(model, field['name'])
            except AttributeError:
                # schema changed, update the registry;
                model = cls.create_subclass(model_name, schema)
                registry.update(model_name, model)
                break

        return model


class DataObjectMixin(object):

    @classmethod
    def _get_instance_name(cls, kwargs):
        return cls.please.properties.get('instance_name') or kwargs.get('instance_name')

    @classmethod
    def _get_class_name(cls, kwargs):
        return cls.PREDEFINED_CLASS_NAME

    @classmethod
    def get_class_object(cls):
        return Class.please.get(name=cls.PREDEFINED_CLASS_NAME)

    @classmethod
    def _set_up_object_class(cls, model):
        for field in model._meta.fields:
            if field.has_endpoint_data and field.name == 'class_name':
                if not getattr(model, field.name, None):
                    setattr(model, field.name, getattr(cls, 'PREDEFINED_CLASS_NAME', None))
        setattr(model, 'get_class_object', cls.get_class_object)
        setattr(model, '_get_instance_name', cls._get_instance_name)
        setattr(model, '_get_class_name', cls._get_class_name)
