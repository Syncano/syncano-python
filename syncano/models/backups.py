# -*- coding: utf-8 -*-
from . import fields
from .base import Model
from .instances import Instance


class Backup(Model):
    """
    OO wrapper around backups `link <http://docs.syncano.com/docs/full-backups>`_.

    :ivar label: :class:`~syncano.models.fields.StringField`
    :ivar description: :class:`~syncano.models.fields.StringField`
    :ivar instance: :class:`~syncano.models.fields.StringField`
    :ivar size: :class:`~syncano.models.fields.IntegerField`
    :ivar status: :class:`~syncano.models.fields.StringField`
    :ivar status_info: :class:`~syncano.models.fields.StringField`
    :ivar author: :class:`~syncano.models.fields.ModelField`
    :ivar details: :class:`~syncano.models.fields.JSONField`
    :ivar updated_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar created_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """

    label = fields.StringField(read_only=True)
    description = fields.StringField(read_only=True)

    instance = fields.StringField(read_only=True)
    size = fields.IntegerField(read_only=True)
    status = fields.StringField(read_only=True)
    status_info = fields.StringField(read_only=True)
    author = fields.ModelField('Admin')
    details = fields.JSONField(read_only=True)

    updated_at = fields.DateTimeField(read_only=True, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)
    links = fields.LinksField()

    class Meta:
        parent = Instance
        endpoints = {
            'detail': {
                'methods': ['get', 'delete'],
                'path': '/backups/full/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/backups/full/',
            },
        }

    def schedule_restore(self):
        restore = Restore(backup=self.id).save()
        return restore


class Restore(Model):

    author = fields.ModelField('Admin')
    status = fields.StringField(read_only=True)
    status_info = fields.StringField(read_only=True)
    updated_at = fields.DateTimeField(read_only=True, required=False)
    created_at = fields.DateTimeField(read_only=True, required=False)
    links = fields.LinksField()
    backup = fields.StringField()
    archive = fields.StringField(read_only=True)

    class Meta:
        parent = Instance
        endpoints = {
            'list': {
                'methods': ['get', 'post'],
                'path': '/restores/',
            },
            'detail': {
                'methods': ['get'],
                'path': '/restores/{id}/',
            }
        }
