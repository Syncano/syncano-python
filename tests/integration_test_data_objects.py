# -*- coding: utf-8 -*-
from hashlib import md5

import requests
from syncano.models import Object
from tests.integration_test import InstanceMixin, IntegrationTest

try:
    # python2
    from StringIO import StringIO
except ImportError:
    # python3
    from io import StringIO


class DataObjectFileTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(DataObjectFileTest, cls).setUpClass()

        cls.schema = [
            {'name': 'test_field_a', 'type': 'string'},
            {'name': 'test_field_file', 'type': 'file'},
        ]
        cls.class_name = 'test_object_file'
        cls.initial_field_a = 'some_string'
        cls.file_path = 'tests/test_files/python-logo.png'
        cls.instance.classes.create(
            name=cls.class_name,
            schema=cls.schema
        )
        with open(cls.file_path, 'rb') as f:
            cls.file_md5 = cls.get_file_md5(f.read())

    def test_creating_file_object(self):
        data_object = self._create_object_with_file()
        self.assertEqual(data_object.test_field_a, self.initial_field_a)
        self.assert_file_md5(data_object)

    def test_updating_another_field(self):
        data_object = self._create_object_with_file()
        file_url = data_object.test_field_file

        # no changes made to the file;
        update_string = 'some_other_string'
        data_object.test_field_a = update_string
        data_object.save()

        self.assertEqual(data_object.test_field_file, file_url)
        self.assertEqual(data_object.test_field_a, update_string)
        self.assert_file_md5(data_object)

    def test_updating_file_field(self):
        data_object = self._create_object_with_file()
        file_url = data_object.test_field_file

        update_string = 'updating also field a'
        file_content = 'some example text file;'
        new_file = StringIO(file_content)
        data_object.test_field_file = new_file
        data_object.test_field_a = update_string
        data_object.save()

        self.assertEqual(data_object.test_field_a, update_string)
        self.assertNotEqual(data_object.test_field_file, file_url)

        # check file content;
        file_content_s3 = requests.get(data_object.test_field_file).text
        self.assertEqual(file_content_s3, file_content)

    def test_manager_update(self):
        data_object = self._create_object_with_file()
        file_url = data_object.test_field_file
        # update only string field;
        update_string = 'manager updating'
        Object.please.update(
            id=data_object.id,
            class_name=self.class_name,
            test_field_a=update_string
        )

        data_object = Object.please.get(id=data_object.id)
        self.assertEqual(data_object.test_field_a, update_string)
        # shouldn't change;
        self.assertEqual(data_object.test_field_file, file_url)

        # update also a file;
        new_update_string = 'manager with file update'
        file_content = 'manager file update'
        new_file = StringIO()
        Object.please.update(
            id=data_object.id,
            class_name=self.class_name,
            test_field_a=new_update_string,
            test_field_file=new_file
        )

        data_object = Object.please.get(id=data_object.id)
        self.assertEqual(data_object.test_field_a, new_update_string)
        # should change;
        self.assertNotEqual(data_object.test_field_file, file_url)
        file_content_s3 = requests.get(data_object.test_field_file).text
        self.assertEqual(file_content_s3, file_content)

    def test_manager_create(self):
        create_string = 'manager create'
        with open(self.file_path, 'rb') as f:
            data_object = Object.please.create(
                class_name=self.class_name,
                test_field_a=create_string,
                test_field_file=f
            )

        self.assertEqual(data_object.test_field_a, create_string)
        self.assert_file_md5(data_object)

    @classmethod
    def get_file_md5(cls, file_content):
        return md5(file_content).hexdigest()

    def assert_file_md5(self, data_object):
        file_content = requests.get(data_object.test_field_file).text
        file_md5 = self.get_file_md5(file_content)
        self.assertEqual(self.file_md5, file_md5)

    def _create_object_with_file(self):
        with open('tests/test_files/python-logo.png', 'rb') as f:
            object = Object.please.create(
                class_name=self.class_name,
                test_field_a=self.initial_field_a,
                test_field_file=f,
            )
        return object
