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

    def test_create_file(self):
        hosting = self._create_hosting('created-xyz')
        a_hosting_file = StringIO()
        a_hosting_file.write('h1 {color: #541231;}')
        a_hosting_file.seek(0)

        hosting_file = hosting.upload_file(path='styles/main.css', file=a_hosting_file)
        self.assertEqual(hosting_file.path, 'styles/main.css')

    def test_set_default(self):
        hosting = self._create_hosting('default-xyz')
        hosting = hosting.set_default()
        self.assertTrue('default', hosting.is_default)

    def test_update_file(self):
        hosting = self._create_hosting('update-xyz')
        a_hosting_file = StringIO()
        a_hosting_file.write('h1 {color: #541231;}')
        a_hosting_file.seek(0)

        hosting.upload_file(path='styles/main.css', file=a_hosting_file)

        a_hosting_file = StringIO()
        a_hosting_file.write('h2 {color: #541231;}')
        a_hosting_file.seek(0)

        hosting_file = hosting.update_file(path='styles/main.css', file=a_hosting_file)
        self.assertEqual(hosting_file.path, 'styles/main.css')

    def _create_hosting(self, name):
        return self.instance.hostings.create(
            name=name,
            description='desc',
            domains=['test.test{}.io'.format(uuid.uuid4().hex[:5])]
        )
