# -*- coding: utf-8 -*-
try:
    # python2
    from StringIO import StringIO
except ImportError:
    # python3
    from io import StringIO

from tests.integration_test import InstanceMixin, IntegrationTest


class HostingIntegrationTests(InstanceMixin, IntegrationTest):

    def setUp(self):
        self.hosting = self.instance.hostings.create(
            label='test12',
            description='desc',
            domains=['test.test.io']
        )

    def test_create_file(self):
        a_hosting_file = StringIO()
        a_hosting_file.write('h1 {color: #541231;}')
        a_hosting_file.seek(0)

        self.hosting.upload_file(path='styles/main.css', file=a_hosting_file)

        files_list = self.hosting.list_files()

        self.assertIn('styles/mains.css', files_list)
