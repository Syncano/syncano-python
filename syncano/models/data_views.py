import json

import six
from syncano.exceptions import SyncanoValueError
from syncano.models.incentives import ResponseTemplate

from . import fields
from .base import Model, Object
from .instances import Instance


class DataEndpoint(Model):
    """
    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar description: :class:`~syncano.models.fields.StringField`
    :ivar query: :class:`~syncano.models.fields.SchemaField`
    :ivar class_name: :class:`~syncano.models.fields.StringField`
    :ivar excluded_fields: :class:`~syncano.models.fields.StringField`
    :ivar expand: :class:`~syncano.models.fields.StringField`
    :ivar order_by: :class:`~syncano.models.fields.StringField`
    :ivar page_size: :class:`~syncano.models.fields.IntegerField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """

    PERMISSIONS_CHOICES = (
        {'display_name': 'None', 'value': 'none'},
        {'display_name': 'Read', 'value': 'read'},
        {'display_name': 'Write', 'value': 'write'},
        {'display_name': 'Full', 'value': 'full'},
    )

    name = fields.StringField(max_length=64, primary_key=True)
    description = fields.StringField(required=False)

    query = fields.JSONField(read_only=False, required=False)

    class_name = fields.StringField(label='class name', mapping='class')

    excluded_fields = fields.StringField(required=False)
    expand = fields.StringField(required=False)
    order_by = fields.StringField(required=False)
    page_size = fields.IntegerField(required=False)

    links = fields.LinksField()

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['get', 'put', 'patch', 'delete'],
                'path': '/endpoints/data/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/endpoints/data/',
            },
            'get': {
                'methods': ['get'],
                'path': '/endpoints/data/{name}/get/',
            },
            'rename': {
                'methods': ['post'],
                'path': '/endpoints/data/{name}/rename/',
            },
            'clear_cache': {
                'methods': ['post'],
                'path': '/endpoints/data/{name}/clear_cache/',
            }
        }

    def rename(self, new_name):
        properties = self.get_endpoint_data()
        http_method = 'POST'
        endpoint = self._meta.resolve_endpoint('rename', properties, http_method)
        connection = self._get_connection()
        return connection.request(http_method,
                                  endpoint,
                                  data={'new_name': new_name})

    def clear_cache(self):
        properties = self.get_endpoint_data()
        http_method = 'POST'
        endpoint = self._meta.resolve_endpoint('clear_cache', properties, http_method)
        connection = self._get_connection()
        return connection.request(http_method, endpoint)

    def get(self, cache_key=None, response_template=None, **kwargs):
        connection = self._get_connection()
        properties = self.get_endpoint_data()
        query = Object.please._build_query(query_data=kwargs, class_name=self.class_name)

        http_method = 'GET'
        endpoint = self._meta.resolve_endpoint('get', properties, http_method)

        kwargs = {}
        params = {}
        params.update({'query': json.dumps(query)})

        if cache_key is not None:
            params = {'cache_key': cache_key}

        if params:
            kwargs = {'params': params}

        if response_template:
            template_name = self._get_response_template_name(response_template)
            kwargs['headers'] = {
                'X-TEMPLATE-RESPONSE': template_name
            }

        while endpoint is not None:
            response = connection.request(http_method, endpoint, **kwargs)
            if isinstance(response, six.string_types):
                endpoint = None
                yield response
            else:
                endpoint = response.get('next')
                for obj in response['objects']:
                    yield obj

    def _get_response_template_name(self, response_template):
        name = response_template
        if isinstance(response_template, ResponseTemplate):
            name = response_template.name
        if not isinstance(name, six.string_types):
            raise SyncanoValueError(
                'Invalid response_template. Must be template\'s name or ResponseTemplate object.'
            )
        return name

    def add_object(self, **kwargs):
        return Object(instance_name=self.instance_name, class_name=self.class_name, **kwargs).save()
