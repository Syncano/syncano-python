# -*- coding: utf-8 -*-
import time

from syncano.models import Backup, Class, Instance
from tests.integration_test import InstanceMixin, IntegrationTest


class FullBackupTestCase(InstanceMixin, IntegrationTest):

    def _test_backup_create(self):
        new_backup = Backup()
        backup_test = new_backup.save()

        backup = Backup.please.get(id=backup_test.id)
        self.assertTrue(backup)
        self.assertEqual(backup.id, backup_test.id)
        self.assertEqual(backup.author.email, self.API_EMAIL)

        return backup.id

    def _test_backup_detail(self, backup_id):
        backup = Backup.please.get(id=backup_id)

        self.assertEqual(backup.id, backup_id)
        self.assertEqual(backup.author.email, self.API_EMAIL)

    def _test_backup_list(self):

        backups = [backup for backup in Backup.please.list()]
        self.assertTrue(len(backups))  # at least one backup here;

    def _test_backup_restore(self, backup_id):
        backup = Backup.please.get(id=backup_id)
        instance_name = backup.instance
        instance = Instance.please.get(name=instance_name)
        classes_count = len(list(instance.classes))

        test_class = Class(name='testclass')
        test_class.save()
        instance.reload()
        classes_count_after_update = len(list(instance.classes))

        self.assertTrue(
            classes_count_after_update - classes_count == 1,
            'There should be only 1 more instance class after new class creation.'
        )

        # wait for backup to be truly saved and restored
        while backup.status != 'success':
            time.sleep(1)
            backup.reload()
        backup.restore()
        time.sleep(15)

        instance.reload()
        classes_count_after_restore = len(list(instance.classes))

        self.assertEqual(
            classes_count,
            classes_count_after_restore,
            'Classes count after restore should be equal to original classes count.'
        )

    def _test_backup_delete(self, backup_id):
        backup = Backup.please.get(id=backup_id)
        backup.delete()
        backups = [backup_object for backup_object in Backup.please.list()]
        self.assertEqual(len(backups), 0)

    def test_backup(self):
        # we provide one test for all functionality to avoid creating too many backups;
        backup_id = self._test_backup_create()
        self._test_backup_list()
        self._test_backup_detail(backup_id=backup_id)
        self._test_backup_restore(backup_id=backup_id)
        self._test_backup_delete(backup_id=backup_id)
