# -*- coding: utf-8 -*-
import uuid

from tests.integration_test import InstanceMixin, IntegrationTest

try:
    # python2
    from StringIO import StringIO
except ImportError:
    # python3
    from io import StringIO


class HostingIntegrationTests(InstanceMixin, IntegrationTest):

    def setUp(self):
        self.hosting = self.instance.hostings.create(
            name='test12',
            description='desc',
            domains=['test.test{}.io'.format(uuid.uuid4().hex[:5])]
        )

    def test_create_file(self):
        a_hosting_file = StringIO()
        a_hosting_file.write('h1 {color: #541231;}')
        a_hosting_file.seek(0)

        hosting_file = self.hosting.upload_file(path='styles/main.css', file=a_hosting_file)
        self.assertEqual(hosting_file.path, 'styles/main.css')

    def test_set_default(self):
        hosting = self.hosting.set_default()
        self.assertTrue('default', hosting.is_default)

    def test_update_file(self):
        a_hosting_file = StringIO()
        a_hosting_file.write('h1 {color: #541231;}')
        a_hosting_file.seek(0)

        self.hosting.upload_file(path='styles/main.css', file=a_hosting_file)

        a_hosting_file = StringIO()
        a_hosting_file.write('h2 {color: #541231;}')
        a_hosting_file.seek(0)

        hosting_file = self.hosting.update_file(path='styles/main.css', file=a_hosting_file)
        self.assertEqual(hosting_file.path, 'styles/main.css')
