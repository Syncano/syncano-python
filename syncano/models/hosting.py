# -*- coding: utf-8 -*-

from . import fields
from .base import Model
from .instances import Instance


class Hosting(Model):
    """
        OO wrapper around hosting.
    """

    name = fields.StringField(max_length=253)
    is_default = fields.BooleanField(read_only=True)
    is_active = fields.BooleanField(default=True)
    description = fields.StringField(read_only=False, required=False)
    domains = fields.ListField(default=[])

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
        """
        Upload a new file to the hosting.
        :param path: the file path;
        :param file: the file to be uploaded;
        :return: the response from the API;
        """
        files_path = self.links.files
        data = {'path': path}
        connection = self._get_connection()
        headers = self._prepare_header(connection)
        response = connection.session.post('{}{}'.format(connection.host, files_path), headers=headers,
                                           data=data, files=[('file', file)])
        if response.status_code != 201:
            return
        return HostingFile(**response.json())

    def update_file(self, path, file):
        """
        Updates an existing file.
        :param path: the file path;
        :param file: the file to be uploaded;
        :return: the response from the API;
        """
        hosting_files = self._get_files()
        is_found = False

        for hosting_file in hosting_files:
            if hosting_file.path == path:
                is_found = True
                break

        if not is_found:
            # create if not found;
            hosting_file = self.upload_file(path, file)
            return hosting_file

        connection = self._get_connection()
        headers = self._prepare_header(connection)
        response = connection.session.patch('{}{}'.format(connection.host, hosting_file.links.self), headers=headers,
                                            files=[('file', file)])
        if response.status_code != 200:
            return
        return HostingFile(**response.json())

    def list_files(self):
        return self._get_files()

    def set_default(self):
        default_path = self.links.set_default
        connection = self._get_connection()

        response = connection.make_request('POST', default_path)
        self.to_python(response)
        return self

    def _prepare_header(self, connection):
        params = connection.build_params(params={})
        headers = params['headers']
        headers.pop('content-type')
        return headers

    def _get_files(self):
        return [hfile for hfile in HostingFile.please.list(hosting_id=self.id)]


class HostingFile(Model):
    """
        OO wrapper around hosting file.
    """

    path = fields.StringField(max_length=300)
    file = fields.FileField()
    links = fields.LinksField()

    class Meta:
        parent = Hosting
        endpoints = {
            'detail': {
                'methods': ['delete', 'get', 'put', 'patch'],
                'path': '/files/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/files/',
            }
        }
