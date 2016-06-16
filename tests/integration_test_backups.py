# -*- coding: utf-8 -*-
from syncano.models import Backup, PartialBackup
from tests.integration_test import InstanceMixin, IntegrationTest


class BaseBackupTestCase(InstanceMixin, IntegrationTest):

    BACKUP_MODEL = {
        'full': Backup,
        'partial': PartialBackup,
    }

    def _get_backup_model(self, backup_type):
        return self.BACKUP_MODEL.get(backup_type)

    def _test_backup_create(self, backup_type='full', query_args=None):
        backup_model = self._get_backup_model(backup_type)
        if query_args is not None:
            new_backup = backup_model(query_args=query_args)
        else:
            new_backup = backup_model()
        backup_test = new_backup.save()

        backup = backup_model.please.get(id=backup_test.id)
        self.assertTrue(backup)
        self.assertEqual(backup.id, backup_test.id)
        self.assertEqual(backup.author.email, self.API_EMAIL)

        return backup.id

    def _test_backup_detail(self, backup_id, backup_type='full'):
        backup_model = self._get_backup_model(backup_type)
        backup = backup_model.please.get(id=backup_id)

        self.assertEqual(backup.id, backup_id)
        self.assertEqual(backup.author.email, self.API_EMAIL)

    def _test_backup_list(self, backup_type='full'):
        backup_model = self._get_backup_model(backup_type)
        backups = [backup for backup in backup_model.please.list()]
        self.assertTrue(len(backups))  # at least one backup here;

    def _test_backup_delete(self, backup_id, backup_type='full'):
        backup_model = self._get_backup_model(backup_type)
        backup = backup_model.please.get(id=backup_id)
        backup.delete()
        backups = [backup_object for backup_object in backup_model.please.list()]
        self.assertEqual(len(backups), 0)


class FullBackupTestCase(BaseBackupTestCase):

    def test_backup(self):
        # we provide one test for all functionality to avoid creating too many backups;
        backup_id = self._test_backup_create()
        self._test_backup_list()
        self._test_backup_detail(backup_id=backup_id)
        self._test_backup_delete(backup_id=backup_id)


class PartialBackupTestCase(BaseBackupTestCase):

    def test_backup(self):
        # we provide one test for all functionality to avoid creating too many backups;
        backup_id = self._test_backup_create(backup_type='partial', query_args={'class': ['user_profile']})
        self._test_backup_list(backup_type='partial')
        self._test_backup_detail(backup_id=backup_id, backup_type='partial')
        self._test_backup_delete(backup_id=backup_id, backup_type='partial')
