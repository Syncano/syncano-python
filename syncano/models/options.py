import re
from bisect import bisect

import six
from syncano.connection import ConnectionMixin
from syncano.exceptions import SyncanoValueError
from syncano.models.registry import registry
from syncano.utils import camelcase_to_underscore

if six.PY3:
    from urllib.parse import urljoin
else:
    from urlparse import urljoin


class Options(ConnectionMixin):
    """Holds metadata related to model definition."""

    def __init__(self, meta=None):
        self.name = None
        self.plural_name = None
        self.related_name = None

        self.parent = None
        self.parent_properties = []
        self.parent_resolved = False

        self.endpoints = {}
        self.endpoint_fields = set()

        self.fields = []
        self.field_names = []

        self.pk = None

        if meta:
            meta_attrs = meta.__dict__.copy()
            for name in meta.__dict__:
                if name.startswith('_') or not hasattr(self, name):
                    del meta_attrs[name]

            for name, value in six.iteritems(meta_attrs):
                setattr(self, name, value)

        self.build_properties()

    def build_properties(self):
        for name, endpoint in six.iteritems(self.endpoints):
            if 'properties' not in endpoint:
                properties = self.get_path_properties(endpoint['path'])
                endpoint['properties'] = properties
                self.endpoint_fields.update(properties)

    def contribute_to_class(self, cls, name):
        if not self.name:
            model_name = camelcase_to_underscore(cls.__name__)
            self.name = model_name.replace('_', ' ').capitalize()

        if not self.plural_name:
            self.plural_name = '{0}s'.format(self.name)

        if not self.related_name:
            self.related_name = self.plural_name.replace(' ', '_').lower()

        if self.parent and isinstance(self.parent, six.string_types):
            self.parent = registry.get_model_by_name(self.parent)

        self.resolve_parent_data()

        setattr(cls, name, self)

    def resolve_parent_data(self):
        if not self.parent or self.parent_resolved:
            return

        parent_meta = self.parent._meta
        parent_name = parent_meta.name.replace(' ', '_').lower()
        parent_endpoint = parent_meta.get_endpoint('detail')
        prefix = parent_endpoint['path']

        for prop in parent_endpoint.get('properties', []):
            if prop in parent_meta.field_names and prop not in parent_meta.parent_properties:
                prop = '{0}_{1}'.format(parent_name, prop)
            self.parent_properties.append(prop)

        for old, new in zip(parent_endpoint['properties'], self.parent_properties):
            prefix = prefix.replace(
                '{{{0}}}'.format(old),
                '{{{0}}}'.format(new)
            )

        for name, endpoint in six.iteritems(self.endpoints):
            endpoint['properties'] = self.parent_properties + endpoint['properties']
            endpoint['path'] = urljoin(prefix, endpoint['path'].lstrip('/'))
            self.endpoint_fields.update(endpoint['properties'])

        self.parent_resolved = True

    def add_field(self, field):
        if field.name in self.field_names:
            raise SyncanoValueError('Field "{0}" already defined'.format(field.name))

        self.field_names.append(field.name)
        self.fields.insert(bisect(self.fields, field), field)

    def get_field(self, field_name):
        if not field_name:
            raise SyncanoValueError('Field name is required.')

        if not isinstance(field_name, six.string_types):
            raise SyncanoValueError('Field name should be a string.')

        for field in self.fields:
            if field.name == field_name:
                return field

        raise SyncanoValueError('Field "{0}" not found.'.format(field_name))

    def get_endpoint(self, name):
        if name not in self.endpoints:
            raise SyncanoValueError('Invalid path name: "{0}".'.format(name))
        return self.endpoints[name]

    def get_endpoint_properties(self, name):
        endpoint = self.get_endpoint(name)
        return endpoint['properties']

    def get_endpoint_path(self, name):
        endpoint = self.get_endpoint(name)
        return endpoint['path']

    def get_endpoint_methods(self, name):
        endpoint = self.get_endpoint(name)
        return endpoint['methods']

    def resolve_endpoint(self, name, properties):
        endpoint = self.get_endpoint(name)

        for name in endpoint['properties']:
            if name not in properties:
                raise SyncanoValueError('Request property "{0}" is required.'.format(name))

        return endpoint['path'].format(**properties)

    def get_endpoint_query_params(self, name, params):
        properties = self.get_endpoint_properties(name)
        return {k: v for k, v in six.iteritems(params) if k not in properties}

    def get_path_properties(self, path):
        return re.findall('/{([^}]*)}', path)
