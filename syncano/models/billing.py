

from . import fields
from .base import Model


class Coupon(Model):
    """
    OO wrapper around coupons `link <TODO>`_.

    :ivar name: :class:`~syncano.models.fields.StringField`
    :ivar redeem_by: :class:`~syncano.models.fields.DateField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    :ivar percent_off: :class:`~syncano.models.fields.IntegerField`
    :ivar amount_off: :class:`~syncano.models.fields.FloatField`
    :ivar currency: :class:`~syncano.models.fields.ChoiceField`
    :ivar duration: :class:`~syncano.models.fields.IntegerField`
    """

    CURRENCY_CHOICES = (
        {'display_name': 'USD', 'value': 'usd'},
    )

    name = fields.StringField(max_length=32, primary_key=True)
    redeem_by = fields.DateField()
    links = fields.LinksField()
    percent_off = fields.IntegerField(required=False)
    amount_off = fields.FloatField(required=False)
    currency = fields.ChoiceField(choices=CURRENCY_CHOICES)
    duration = fields.IntegerField(default=0)

    class Meta:
        endpoints = {
            'detail': {
                'methods': ['get', 'delete'],
                'path': '/v1.1/billing/coupons/{name}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/v1.1/billing/coupons/',
            }
        }


class Discount(Model):
    """
    OO wrapper around discounts `link <TODO>`_.

    :ivar instance: :class:`~syncano.models.fields.ModelField`
    :ivar coupon: :class:`~syncano.models.fields.ModelField`
    :ivar start: :class:`~syncano.models.fields.DateField`
    :ivar end: :class:`~syncano.models.fields.DateField`
    :ivar links: :class:`~syncano.models.fields.HyperlinkedField`
    """

    instance = fields.ModelField('Instance')
    coupon = fields.ModelField('Coupon')
    start = fields.DateField(read_only=True, required=False)
    end = fields.DateField(read_only=True, required=False)
    links = fields.LinksField()

    class Meta:
        endpoints = {
            'detail': {
                'methods': ['get'],
                'path': '/v1.1/billing/discounts/{id}/',
            },
            'list': {
                'methods': ['post', 'get'],
                'path': '/v1.1/billing/discounts/',
            }
        }
