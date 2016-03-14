

from . import fields
from .base import Model
from .custom_response import CustomResponseMixin
from .incentives import Schedule, Script, ScriptEndpoint, Trigger


class ScriptTrace(CustomResponseMixin, Model):
    """
    :ivar status: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar executed_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar result: :class:`~syncano.models.fields.StringField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """
    STATUS_CHOICES = (
        {'display_name': 'Success', 'value': 'success'},
        {'display_name': 'Failure', 'value': 'failure'},
        {'display_name': 'Timeout', 'value': 'timeout'},
        {'display_name': 'Processing', 'value': 'processing'},
        {'display_name': 'Pending', 'value': 'pending'},
    )

    status = fields.ChoiceField(choices=STATUS_CHOICES, read_only=True, required=False)
    links = fields.LinksField()
    executed_at = fields.DateTimeField(read_only=True, required=False)
    result = fields.JSONField(read_only=True, required=False)
    duration = fields.IntegerField(read_only=True, required=False)

    class Meta:
        parent = Script
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/traces/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/traces/',
            }
        }


class ScheduleTrace(Model):
    """
    :ivar status: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar executed_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar result: :class:`~syncano.models.fields.StringField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """
    STATUS_CHOICES = (
        {'display_name': 'Success', 'value': 'success'},
        {'display_name': 'Failure', 'value': 'failure'},
        {'display_name': 'Timeout', 'value': 'timeout'},
        {'display_name': 'Pending', 'value': 'pending'},
    )

    status = fields.ChoiceField(choices=STATUS_CHOICES, read_only=True, required=False)
    links = fields.LinksField()
    executed_at = fields.DateTimeField(read_only=True, required=False)
    result = fields.StringField(read_only=True, required=False)
    duration = fields.IntegerField(read_only=True, required=False)

    class Meta:
        parent = Schedule
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/traces/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/traces/',
            }
        }


class TriggerTrace(Model):
    """
    :ivar status: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar executed_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar result: :class:`~syncano.models.fields.StringField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """
    STATUS_CHOICES = (
        {'display_name': 'Success', 'value': 'success'},
        {'display_name': 'Failure', 'value': 'failure'},
        {'display_name': 'Timeout', 'value': 'timeout'},
        {'display_name': 'Pending', 'value': 'pending'},
    )
    LINKS = (
        {'type': 'detail', 'name': 'self'},
    )

    status = fields.ChoiceField(choices=STATUS_CHOICES, read_only=True, required=False)
    links = fields.LinksField()
    executed_at = fields.DateTimeField(read_only=True, required=False)
    result = fields.StringField(read_only=True, required=False)
    duration = fields.IntegerField(read_only=True, required=False)

    class Meta:
        parent = Trigger
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/traces/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/traces/',
            }
        }


class ScriptEndpointTrace(CustomResponseMixin, Model):
    """
    :ivar status: :class:`~syncano.models.fields.ChoiceField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar executed_at: :class:`~syncano.models.fields.DateTimeField`
    :ivar result: :class:`~syncano.models.fields.StringField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """
    STATUS_CHOICES = (
        {'display_name': 'Success', 'value': 'success'},
        {'display_name': 'Failure', 'value': 'failure'},
        {'display_name': 'Timeout', 'value': 'timeout'},
        {'display_name': 'Pending', 'value': 'pending'},
    )

    status = fields.ChoiceField(choices=STATUS_CHOICES, read_only=True, required=False)
    links = fields.LinksField()
    executed_at = fields.DateTimeField(read_only=True, required=False)
    result = fields.JSONField(read_only=True, required=False)
    duration = fields.IntegerField(read_only=True, required=False)

    class Meta:
        parent = ScriptEndpoint
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/traces/{id}/',
            },
            'list': {
                'methods': ['get'],
                'path': '/traces/',
            }
        }
