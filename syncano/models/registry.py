from __future__ import unicode_literals

import six
import re

from syncano import logger
from syncano.exceptions import SyncanoValueError

from .base import Model
from .fields import MAPPING
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

    def register_definition(self, definition):
        Meta = type(str('Meta'), (Options, ), {
            'connection': self.connection,
            'endpoints': definition['endpoints'],
            'name': definition['name'],
        })

        attrs = {'Meta': Meta}
        for name, options in six.iteritems(definition.get('properties', {})):
            field_type = options.pop('type', 'field')  # TODO: Nested objects

            if field_type not in MAPPING:
                raise SyncanoValueError('Invalid field type "{0}".'.format(field_type))

            attrs[name] = MAPPING[field_type](**options)

        cls = type(str(definition['name']), (Model, ), attrs)
        self.register_model(definition['name'], cls)

        return self

    def register_schema(self, schema):
        for definition in schema:
            self.register_definition(definition)
        return self
