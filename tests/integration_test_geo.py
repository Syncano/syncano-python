# -*- coding: utf-8 -*-
import six
from syncano.models import Class, GeoPoint, Object
from tests.integration_test import InstanceMixin, IntegrationTest


class GeoPointApiTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(GeoPointApiTest, cls).setUpClass()

        cls.city_model = Class.please.create(instance_name=cls.instance.name, name='city', schema=[
            {"name": "city", "type": "string"},
            {"name": "location", "type": "geopoint", "filter_index": True},
        ])

        cls.warsaw = Object.please.create(instance_name=cls.instance.name,
                                          class_name='city', location=(52.2240698, 20.9942933), city='Warsaw')
        cls.paris = Object.please.create(instance_name=cls.instance.name,
                                         class_name='city', location=(52.4731384, 13.5425588), city='Berlin')
        cls.berlin = Object.please.create(instance_name=cls.instance.name,
                                          class_name='city', location=(48.8589101, 2.3125377), city='Paris')
        cls.london = Object.please.create(instance_name=cls.instance.name,
                                          class_name='city', city='London')

        cls.list_london = ['London']
        cls.list_warsaw = ['Warsaw']
        cls.list_warsaw_berlin = ['Warsaw', 'Berlin']
        cls.list_warsaw_berlin_paris = ['Warsaw', 'Berlin', 'Paris']

    def test_filtering_on_geo_point_near(self):

        distances = {
            100: self.list_warsaw,
            600: self.list_warsaw_berlin,
            1400: self.list_warsaw_berlin_paris
        }

        for distance, cities in six.iteritems(distances):
            objects = Object.please.list(instance_name=self.instance.name, class_name="city").filter(
                geo_point__near={
                    "latitude": 52.2297,
                    "longitude": 21.0122,
                    "distance": distance,
                    "unit": GeoPoint.KILOMETERS
                }
            )

            result_list = self._prepare_result_list(objects)

            self.assertListEqual(result_list, cities)

    def test_filtering_on_geo_pint_near_miles(self):
        objects = Object.please.list(instance_name=self.instance.name, class_name="city").filter(
            geo_point__near={
                "latitude": 52.2297,
                "longitude": 21.0122,
                "distance": 10,
                "unit": GeoPoint.MILES
            }
        )
        result_list = self._prepare_result_list(objects)
        self.assertListEqual(result_list, self.list_warsaw)

    def test_filtering_on_geo_point_exists(self):
        objects = Object.please.list(instance_name=self.instance.name, class_name="geo_klass").filter(
            geo_point__exists=True
        )

        result_list = [o.city for o in objects]

        self.assertListEqual(result_list, self.list_warsaw_berlin_paris)

        objects = Object.please.list(instance_name=self.instance.name, class_name="geo_klass").filter(
            geo_point__exists=False
        )

        result_list = self._prepare_result_list(objects)

        self.assertListEqual(result_list, self.list_london)

    def _prepare_result_list(self, objects):
        return [o.city for o in objects]
