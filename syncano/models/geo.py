# -*- coding: utf-8 -*-
from syncano.exceptions import SyncanoValueError


class GeoPoint(object):

    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return "GeoPoint(latitude={}, longitude={})".format(self.latitude, self.longitude)

    def to_native(self):
        geo_struct_dump = {'latitude': self.latitude, 'longitude': self.longitude}
        return geo_struct_dump


class Distance(object):

    KILOMETERS = '_in_kilometers'
    MILES = '_in_miles'

    def __init__(self, kilometers=None, miles=None):
        if kilometers is not None and miles is not None:
            raise SyncanoValueError('`kilometers` and `miles` can not be set at the same time.')

        if kilometers is None and miles is None:
            raise SyncanoValueError('`kilometers` or `miles` attribute should be specified.')

        self.distance = kilometers or miles
        self.unit = self.KILOMETERS if kilometers is not None else self.MILES

    def to_native(self):
        return {
            'distance{}'.format(self.unit): self.distance
        }
