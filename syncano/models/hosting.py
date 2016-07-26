# -*- coding: utf-8 -*-
from . import fields
from .base import Instance, Model, logger


class Hosting(Model):
    """
        OO wrapper around hosting.
    """

    label = fields.StringField(max_length=64, primary_key=True)
    description = fields.StringField(read_only=False, required=False)
    domains = fields.ListField(default=[])

    id = fields.IntegerField(read_only=True)
    links = fields.LinksField()
    created_at = fields.DateTimeField(read_only=True, required=False)
    updated_at = fields.DateTimeField(read_only=True, required=False)

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['delete', 'get', 'put', 'patch'],
                'path': '/hosting/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/hosting/',
            }
        }

    def upload_file(self, path, file):
        files_path = self.links.files
        data = {'path': path}
        connection = self._get_connection()
        params = connection.build_params(params={})
        headers = params['headers']
        headers.pop('content-type')
        response = connection.session.post(connection.host + files_path, headers=headers,
                                           data=data, files=[('file', file)])
        if response.status_code != 201:
            logger.error(response.text)
            return
        return response

    def list_files(self):
        files_path = self.links.files
        connection = self._get_connection()
        response = connection.request('GET', files_path)
        return [f['path'] for f in response['objects']]

    def set_default(self):
        default_path = self.links.set_default
        connection = self._get_connection()

        response = connection.make_request('POST', default_path)
        self.to_python(response)
        return self
