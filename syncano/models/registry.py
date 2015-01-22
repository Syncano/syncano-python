from __future__ import unicode_literals

import re

from syncano import logger
from syncano.exceptions import SyncanoValueError

from .base import Model
from .fields import ModelField, HyperlinkeField, MAPPING
from .options import Options


class Registry(object):

    def __init__(self, connection, models=None):
        self.connection = connection
        self.models = models or {}
        self.patterns = []

    def __str__(self):
        return 'Registry: {0}'.format(', '.join(self.models))

    def __unicode__(self):
        return unicode(str(self))

    def __iter__(self):
        for name, model in self.models.iteritems():
            yield model

    def get_model_patterns(self, cls):
        patterns = []
        for k, v in cls._meta.endpoints.iteritems():
            pattern = '^{0}$'.format(v['path'])
            for name, value in v.get('properties', {}).iteritems():
                pattern = pattern.replace('{{{0}}}'.format(name), '([^/.]+)')
            patterns.append((re.compile(pattern), cls))
        return patterns

    def get_model_by_path(self, path):
        for pattern, cls in self.patterns:
            if pattern.match(path):
                return cls

    def get_model_by_name(self, path):
        raise NotImplementedError

    def get_model_by_id(self, path):
        raise NotImplementedError

    def register_model(self, name, cls):
        if name not in self.models:
            logger.debug('Registry: %s', name)

            self.models[name] = cls
            patterns = self.get_model_patterns(cls)
            self.patterns.extend(patterns)

            setattr(self, str(name), cls)
        return self

    def register_definition(self, definition, model_ids=None):
        Meta = type(str('Meta'), (Options, ), {
            'connection': self.connection,
            'endpoints': definition['endpoints'],
            'name': definition['name'],
            'id': definition['id'],
        })

        attrs = {
            'Meta': Meta,
            'links': HyperlinkeField(read_only=True, required=False)
        }
        for name, options in definition.get('properties', {}).iteritems():
            field_type = options.pop('type')

            if field_type in model_ids:
                field_attr = ModelField(field_type, **options)
            elif field_type in MAPPING:
                field_attr = MAPPING[field_type](**options)
            else:
                raise SyncanoValueError('Invalid field type "{0}".'.format(field_type))

            attrs[name] = field_attr

        cls = type(str(definition['name']), (Model, ), attrs)
        self.register_model(definition['name'], cls)

        return self

    def register_schema(self, schema):
        model_ids = [definition['id'] for definition in schema]

        for definition in schema:
            self.register_definition(definition, model_ids)

        return self
