# -*- coding: utf-8 -*-
from syncano.models import Object
from tests.integration_test import InstanceMixin, IntegrationTest


class StringFilteringTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(StringFilteringTest, cls).setUpClass()
        cls.klass = cls.instance.classes.create(name='class_a',
                                                schema=[{'name': 'title', 'type': 'string', 'filter_index': True}])
        cls.object = cls.klass.objects.create(title='Some great title')

    def _test_filter(self, filter):
        filtered_obj = Object.please.list(class_name='class_a').filter(
            **filter
        ).first()

        self.assertTrue(filtered_obj.id)

    def test_starstwith(self):
        self._test_filter({'title__startswith': 'Some'})
        self._test_filter({'title__istartswith': 'omes'})

    def test_endswith(self):
        self._test_filter({'title__endswith': 'tle'})
        self._test_filter({'title__iendswith': 'TLE'})

    def test_contains(self):
        self._test_filter({'title__contains': 'gre'})
        self._test_filter({'title__icontains': 'gRe'})

    def test_eq(self):
        self._test_filter({'title__ieq': 'some gREAt title'})
