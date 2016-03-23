

import re

import six
from syncano import logger


class Registry(object):
    """Models registry.
    """
    def __init__(self, models=None):
        self.models = models or {}
        self.schemas = {}
        self.patterns = []
        self._pending_lookups = {}
        self.instance_name = None
        self._default_connection = None

    def __str__(self):
        return 'Registry: {0}'.format(', '.join(self.models))

    def __unicode__(self):
        return six.u(str(self))

    def __iter__(self):
        for name, model in six.iteritems(self.models):
            yield model

    def get_model_patterns(self, cls):
        patterns = []
        for k, v in six.iteritems(cls._meta.endpoints):
            pattern = '^{0}$'.format(v['path'])
            for name in v.get('properties', []):
                pattern = pattern.replace('{{{0}}}'.format(name), '([^/.]+)')
            patterns.append((re.compile(pattern), cls))
        return patterns

    def get_model_by_path(self, path):
        for pattern, cls in self.patterns:
            if pattern.match(path):
                return cls
        raise LookupError('Invalid path: {0}'.format(path))

    def get_model_by_name(self, name):
        return self.models[name]

    def update(self, name, cls):
        self.models[name] = cls
        related_name = cls._meta.related_name
        patterns = self.get_model_patterns(cls)
        self.patterns.extend(patterns)

        setattr(self, str(name), cls)
        setattr(self, str(related_name), cls.please.all())

        logger.debug('New model: %s, %s', name, related_name)

    def add(self, name, cls):

        if name not in self.models:
            self.update(name, cls)

        if name in self._pending_lookups:
            lookups = self._pending_lookups.pop(name)
            for callback, args, kwargs in lookups:
                callback(*args, **kwargs)

        return self

    def set_default_property(self, name, value):
        for model in self:
            if name not in model.__dict__:
                continue

            for field in model._meta.fields:
                if field.name == name:
                    field.default = value

    def set_default_instance(self, value):
        self.set_default_property('instance_name', value)

    def set_used_instance(self, instance):
        if instance and self.instance_name != instance or registry.instance_name is None:
            self.set_default_instance(instance)  # update the registry with last used instance;
            self.instance_name = instance

    def clear_used_instance(self):
        self.instance_name = None
        self.set_default_instance(None)

    def get_schema(self, class_name):
        return self.schemas.get(class_name)

    def set_schema(self, class_name, schema):
        self.schemas[class_name] = schema

    def clear_schemas(self):
        self.schemas = {}

    def set_default_connection(self, default_connection):
        self._default_connection = default_connection

    @property
    def connection(self):
        if not self._default_connection:
            raise Exception('Set the default connection first.')
        return self._default_connection

registry = Registry()
