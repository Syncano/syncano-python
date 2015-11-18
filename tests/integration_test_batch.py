# -*- coding: utf-8 -*-
from syncano.models import Object, User
from tests.integration_test import InstanceMixin, IntegrationTest


class ManagerBatchTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(ManagerBatchTest, cls).setUpClass()
        cls.klass = cls.instance.classes.create(name='class_a', schema=[{'name': 'title', 'type': 'string'}])
        cls.update1 = cls.klass.objects.create(title='update1')
        cls.update2 = cls.klass.objects.create(title='update2')
        cls.update3 = cls.klass.objects.create(title='update3')
        cls.delete1 = cls.klass.objects.create(title='delete1')
        cls.delete2 = cls.klass.objects.create(title='delete2')
        cls.delete3 = cls.klass.objects.create(title='delete3')

    def test_batch_create(self):

        objects = []
        for i in range(5):
            objects.append(Object(instance_name=self.instance.name, class_name=self.klass.name, title=str(i)))

        results = Object.please.bulk_create(*objects)
        for r in results:
            self.assertTrue(isinstance(r, Object))
            self.assertTrue(r.id)
            self.assertTrue(r.title)

        # test batch now:
        results = Object.please.batch(
            self.klass.objects.as_batch().create(title='one'),
            self.klass.objects.as_batch().create(title='two'),
            self.klass.objects.as_batch().create(title='three'),
        )

        for r in results:
            self.assertTrue(isinstance(r, Object))
            self.assertTrue(r.id)
            self.assertTrue(r.title)

    def test_create_batch_users(self):
        users = self.instance.users.bulk_create(
            User(username='Terminator', password='skynet'),
            User(username='Terminator2', password='skynet'),
        )

        self.assertEqual(len(set([u.username for u in users])), 2)

        for user in users:
            self.assertTrue(isinstance(user, User))
            self.assertTrue(user.id)
            self.assertTrue(user.username in ['Terminator', 'Terminator2'])

        # test batch now:
        users = self.instance.users.batch(
            self.instance.users.as_batch().create(username='Terminator3', password='SarahConnor'),
            self.instance.users.as_batch().create(username='Terminator4', password='BigTruckOnRoad'),
        )

        for user in users:
            self.assertTrue(isinstance(user, User))
            self.assertTrue(user.id)
            self.assertTrue(user.username in ['Terminator3', 'Terminator4'])

    def test_batch_update(self):
        updates = Object.please.batch(
            self.klass.objects.as_batch().update(id=self.update1.id, title='FactoryChase'),
            self.klass.objects.as_batch().update(id=self.update1.id, title='Photoplay'),
            self.klass.objects.as_batch().update(id=self.update1.id, title='Intimacy'),
        )

        self.assertEqual(len(set([u.title for u in updates])), 3)

        for u in updates:
            self.assertTrue(u.title in ['FactoryChase', 'Photoplay', 'Intimacy'])

    def test_batch_delete(self):
        deletes = Object.please.batch(
            self.klass.objects.as_batch().delete(id=self.delete1.id),
            self.klass.objects.as_batch().delete(id=self.delete2.id),
        )

        for d in deletes:
            self.assertTrue(d['code'], 204)

    def test_batch_mix(self):
        mix_batches = Object.please.batch(
            self.klass.objects.as_batch().create(title='four'),
            self.klass.objects.as_batch().update(title='TerminatorArrival', id=self.update3.id),
            self.klass.objects.as_batch().delete(id=self.delete3.id)
        )

        # assert create;
        self.assertTrue(mix_batches[0].id)
        self.assertEqual(mix_batches[0].title, 'four')

        # assert update;
        self.assertEqual(mix_batches[1].title, 'TerminatorArrival')

        # assert delete;
        self.assertEqual(mix_batches[2]['code'], 204)
