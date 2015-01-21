from syncano.exceptions import SyncanoValueError


class Options(object):

    def __init__(self, meta=None):
        self.id = None
        self.name = None
        self.endpoints = {}
        self.fields = []
        self.connection = None

        if meta:
            meta_attrs = meta.__dict__.copy()
            for name in meta.__dict__:
                if name.startswith('_') or not hasattr(self, name):
                    del meta_attrs[name]

            for name, value in meta_attrs.iteritems():
                setattr(self, name, value)

    def add_field(self, field):
        self.fields.append(field)

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

    def resolve_endpoint(self, name, properties):
        endpoint = self.get_endpoint(name)

        for name, schema in endpoint['properties'].iteritems():
            if name not in properties:
                raise SyncanoValueError('Request property "{0}" is required.'.format(name))

        return endpoint['path'].format(**properties)

    def get_endpoint_query_params(self, name, params):
        properties = self.get_endpoint_properties(name)
        return {k: v for k, v in params.iteritems() if k not in properties}
