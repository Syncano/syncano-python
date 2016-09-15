# -*- coding: utf-8 -*-
from datetime import datetime

from syncano.exceptions import UserNotFound
from syncano.models import Group, User
from syncano.models.registry import registry
from tests.integration_test import InstanceMixin, IntegrationTest


class UserProfileTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(UserProfileTest, cls).setUpClass()
        cls.user = cls.instance.users.create(
            username='JozinZBazin',
            password='jezioro',
        )
        cls.SAMPLE_PROFILE_PIC = 'some_url_here'
        cls.ANOTHER_SAMPLE_PROFILE_PIC = 'yet_another_url'

    def test_profile(self):
        self.assertTrue(self.user.profile)
        self.assertEqual(
            self.user.profile.__class__.__name__,
            '{}UserProfileObject'.format(self.instance.name.title())
        )

    def test_profile_klass(self):
        klass = self.user.profile.get_class_object()
        self.assertTrue(klass)
        self.assertEqual(klass.instance_name, self.instance.name)

    def test_profile_change_schema(self):
        klass = self.user.profile.get_class_object()
        klass.schema = [
            {'name': 'profile_pic', 'type': 'string'}
        ]

        klass.save()
        self.user.reload()  # force to refresh profile model;

        self.user.profile.profile_pic = self.SAMPLE_PROFILE_PIC
        self.user.save()
        user = User.please.get(id=self.user.id)
        self.assertEqual(user.profile.profile_pic, self.SAMPLE_PROFILE_PIC)

        # test save directly on profile
        self.user.profile.profile_pic = self.ANOTHER_SAMPLE_PROFILE_PIC
        self.user.profile.save()
        user = User.please.get(id=self.user.id)
        self.assertEqual(user.profile.profile_pic, self.ANOTHER_SAMPLE_PROFILE_PIC)


class UserTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(UserTest, cls).setUpClass()

        cls.group = cls.instance.groups.create(
            label='testgroup'
        )

        cls.additional_instance = cls.connection.Instance.please.create(
            name='testpythonlib%s' % cls.generate_hash()[:10],
            description='IntegrationTest %s' % datetime.now(),
        )
        registry.set_used_instance(cls.instance.name)

    @classmethod
    def tearDownClass(cls):
        super(UserTest, cls).tearDownClass()
        cls.additional_instance.delete()

    def test_if_custom_error_is_raised_on_user_group(self):
        with self.assertRaises(UserNotFound):
            self.group.user_details(user_id=221)

    def test_user_group_membership(self):
        user = User.please.create(
            username='testa',
            password='1234'
        )

        group_test = Group.please.create(label='new_group_a')

        groups = user.list_groups()
        self.assertListEqual(groups, [])

        group = user.add_to_group(group_id=group_test.id)
        self.assertEqual(group.id, group_test.id)
        self.assertEqual(group.label, group_test.label)

        groups = user.list_groups()
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].id, group_test.id)

        group = user.group_details(group_id=group_test.id)
        self.assertEqual(group.id, group_test.id)
        self.assertEqual(group.label, group_test.label)

        response = user.remove_from_group(group_id=group_test.id)
        self.assertIsNone(response)

    def test_group_user_membership(self):
        user_test = User.please.create(
            username='testb',
            password='1234'
        )

        group = Group.please.create(label='new_group_b')

        users = group.list_users()
        self.assertListEqual(users, [])

        user = group.add_user(user_id=user_test.id)
        self.assertEqual(user.id, user_test.id)
        self.assertEqual(user.username, user_test.username)

        users = group.list_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].id, user_test.id)

        user = group.user_details(user_id=user_test.id)
        self.assertEqual(user.id, user_test.id)
        self.assertEqual(user.username, user_test.username)

        response = group.delete_user(user_id=user_test.id)
        self.assertIsNone(response)

    def test_user_retrieval_with_specified_instance_name(self):
        user = self.additional_instance.users.create(
            username='custom_instance_user_123',
            password='password',
        )
        instance_user = User.please.get(id=user.id, instance_name=self.additional_instance.name)
        self.assertEqual(instance_user.id, user.id)
        self.assertEqual(instance_user.username, user.username)
        users = User.please.list(instance_name=self.additional_instance.name)
        self.assertEqual(len(list(users)), 1)
        self.assertEqual(instance_user.id, users[0].id)
        self.assertEqual(instance_user.username, users[0].username)
