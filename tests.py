import unittest
import random
import string
import logging

from syncano.client import SyncanoApi, SyncanoAsyncApi
import syncano.exceptions
import testconfig #variables LOGIN, PASSWORD, INSTANCE, HOST

logging.basicConfig(filename="tests.log", level=logging.INFO)


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


class SyncanoTest(object):

    def setUp(self):
        self.syncano = SyncanoApi(testconfig.INSTANCE, login=testconfig.LOGIN,
                              password=testconfig.PASSWORD, host=testconfig.HOST)

    def tearDown(self):
        self.syncano.close()


class TestInstanceClients(SyncanoTest, unittest.TestCase):

    def setUp(self):
        super(TestInstanceClients, self).setUp()
        self.login = id_generator(10)

    def test_01_create_get_one_get_delete(self):
        client = self.syncano.client_new(self.login, self.login)
        self.client_id = client['data']['client']['id']
        client_2 = self.syncano.client_get_one(self.client_id)
        self.client_2_id = client_2['data']['client']['id']
        assert self.client_id == self.client_2_id, "Client ids don`t match"
        self.syncano.client_delete(client_login=self.login)
        clients = self.syncano.client_get()
        for c in clients['data']['client']:
            assert self.client_id != c['id'], 'Client delete fails'

    def test_02_heartbeat(self):
        self.syncano.client_heartbeat()

    def test_03_get_identities(self):
        identities = self.syncano.client_get_identities()
        assert identities, "No identities response"

    def test_04_get_groups(self):
        groups = self.syncano.client_get_groups()
        assert groups['data']['groups'], 'Any groups'

    def test_05_add_update_delete(self):
        client = self.syncano.client_new(self.login, self.login)
        client_id = client['data']['client']['id']
        client2 = self.syncano.client_update(client_id, first_name=id_generator(6))
        assert client['data']['client']['first_name'] != client2['data']['client']['first_name'], 'Client not updated'
        assert client['data']['client']['id'] == client2['data']['client']['id'], 'Client id changed on update'
        self.syncano.client_delete(client_login=self.login)

    def test_06_login_on_created_client(self):
        self.syncano.client_new(self.login, self.login)
        try:
            syncanoc = SyncanoApi(testconfig.INSTANCE, login=self.login, password=self.login, host=testconfig.HOST)
            syncanoc.close()
        except syncano.exceptions.AuthException:
            assert 1, "Can`t login on a new client account"
        self.syncano.client_delete(client_login=self.login)

    def test_07_update_password(self):
        client = self.syncano.client_new(self.login, self.login)
        new_password = id_generator()
        self.syncano.client_update_password(new_password, client['data']['client']['id'])
        try:
            syncanoc = SyncanoApi(testconfig.INSTANCE, login=self.login, password=self.login, host=testconfig.HOST)
            syncanoc.close()
            assert 1, "Old password works after update password"
        except syncano.exceptions.AuthException:
            pass
        try:
            syncanoc = SyncanoApi(testconfig.INSTANCE, login=self.login, password=new_password, host=testconfig.HOST)
            syncanoc.close()
        except syncano.exceptions.AuthException:
            assert 1, "Can`t login using new password"
        self.syncano.client_delete(client_login=self.login)

    def test_08_update_state(self):
        self.syncano.client_new(self.login, self.login)
        state = id_generator(4)
        self.syncano.client_update_state(state, client_login=self.login)
        client2 = self.syncano.client_get_one(client_login=self.login)
        assert client2['data']['client']['state'] == state, "State doesnt change"
        self.syncano.client_delete(client_login=self.login)

    def test_09_recreate_apikey(self):
        self.syncano.client_new(self.login, self.login)
        api_key =  self.syncano.client_recreate_apikey(client_login=self.login)['data']['api_key']
        try:
            syncano = SyncanoApi(testconfig.INSTANCE, api_key, host=testconfig.HOST)
            syncano.close()
        except syncano.exceptions.AuthException:
            assert 1, "Cant sign in using api_key"
        self.syncano.client_delete(client_login=self.login)


class TestProjects(SyncanoTest, unittest.TestCase):

    def setUp(self):
        super(TestProjects, self).setUp()
        self.project = id_generator()

    def test_01_create__delete_get_one_get(self):
        project = self.syncano.project_new(self.project)
        project_id = project['data']['id']
        project2 = self.syncano.project_get_one(project_id)
        project2_id = project2['data']['project']['id']
        assert project_id == project2_id, "Project ids don`t match %s %s" % (project_id, project2_id)
        self.syncano.project_delete(project_id)
        projects = self.syncano.project.get(message_id=1)
        for p in projects['data']['project']:
            assert p['id'] != project_id, "Project delete failed"


    def test_02_project_new_update_get_one(self):
        project = self.syncano.project_new(self.project)
        project_id = project['data']['id']
        new_project_name = id_generator(8)
        new_project = self.syncano.project_update(project_id, new_project_name, message_id=1)
        assert new_project['data']['project']['id'] == project_id, 'ID changed after update'
        project2 = self.syncano.project_get_one(project_id)
        assert project2['data']['project']['name'] == new_project_name, 'Project name didn`t change'
        self.syncano.project_delete(project_id)


class TestCollections(SyncanoTest, unittest.TestCase):

    def setUp(self):
        super(TestCollections, self).setUp()
        self.project_name = id_generator()
        self.project = self.syncano.project_new(self.project_name)
        self.project_id = self.project['data']['id']
        self.collection_name = id_generator()
        self.collection_key = id_generator()

    def test_01_create_delete_get_one_get(self):
        collection = self.syncano.collection_new(self.project['data']['id'], self.collection_name, self.collection_key)
        self.syncano.collection_activate(self.project['data']['id'], collection_id=collection['data']['collection']['id'])
        collection2 = self.syncano.collection_get_one(self.project['data']['id'],
                                                    collection_id=collection['data']['collection']['id'])
        assert collection['data']['collection']['id'] == collection2['data']['collection']['id'], "Collection not created"
        self.syncano.collection_delete(self.project['data']['id'], collection_key=self.collection_key)
        collections = self.syncano.collection_get(self.project['data']['id'], message_id=6)
        for c in collections['data']['collection']:
            assert c['id'] != collection['data']['collection']['id']

    def test_02_activate_deactivate(self):
        collection = self.syncano.collection_new(self.project_id, self.collection_name, self.collection_key)
        cid = collection['data']['collection']['id']
        collection2 = self.syncano.collection_get_one(self.project_id, cid)
        assert collection2['data']['collection']['status'] == 'inactive', 'Created activated collection'
        self.syncano.collection_activate(self.project_id, cid, self.collection_key)
        collection2 = self.syncano.collection_get_one(self.project_id, cid)
        assert collection2['data']['collection']['status'] == 'active', 'Cant activation fails'
        self.syncano.collection_deactivate(self.project_id, cid, self.collection_key)
        collection2 = self.syncano.collection_get_one(self.project_id, cid)
        assert collection2['data']['collection']['status'] == 'inactive', 'Deactivation fails'
        self.syncano.collection_delete(self.project_id, cid)

    def test_03_inactive_collection_update(self):
        collection = self.syncano.collection_new(self.project_id, self.collection_name, self.collection_key)
        cid = collection['data']['collection']['id']
        new_name, new_key = id_generator(), id_generator()
        collection2 = self.syncano.collection_update(self.project_id, cid, name=new_name, collection_key=new_key)
        assert collection2['data']['collection']['id'] == cid, 'Collection id changed'
        assert collection2['data']['collection']['name'] == new_name, 'Name didnt change'
        assert collection2['data']['collection']['key'] == new_key, 'Key didnt change on update'
        collection2 = self.syncano.collection_get_one(self.project_id, cid)
        assert collection2['data']['collection']['id'] == cid, 'Collection id changed'
        assert collection2['data']['collection']['name'] == new_name, 'Name didnt change'
        assert collection2['data']['collection']['key'] != self.collection_key, 'Key not changed on inactive collection'
        self.syncano.collection_delete(self.project_id, cid)

    def test_05_active_collection_update(self):
        collection = self.syncano.collection_new(self.project_id, self.collection_name, self.collection_key)
        cid = collection['data']['collection']['id']
        self.syncano.collection_activate(self.project_id, cid)
        new_name, new_key = id_generator(), id_generator()
        collection2 = self.syncano.collection_update(self.project_id, cid, name=new_name, collection_key=new_key)
        assert collection2['data']['collection']['id'] == cid, 'Collection id changed'
        assert collection2['data']['collection']['name'] == new_name, 'Name didnt change'
        assert collection2['data']['collection']['key'] == new_key, 'Key didnt change on update'
        collection2 = self.syncano.collection_get_one(self.project_id, cid)
        assert collection2['data']['collection']['id'] == cid, 'Collection id changed'
        assert collection2['data']['collection']['name'] == new_name, 'Name didnt change'
        assert collection2['data']['collection']['key'] != self.collection_key, 'Key not changed on inactive collection'
        self.syncano.collection_delete(self.project_id, cid)

    def test_04_add_tags_delete_tags(self):
        collection = self.syncano.collection_new(self.project_id, self.collection_name, self.collection_key)
        cid = collection['data']['collection']['id']
        self.syncano.collection_activate(self.project_id, cid)
        tag = id_generator(10)
        self.syncano.collection_add_tag(self.project_id, cid, tags=tag, weight=1)
        collection = self.syncano.collection_get_one(self.project_id, collection_key=self.collection_key, message_id=132)
        assert tag in collection['data']['collection']['tags'], 'Tags didnt add'
        self.syncano.collection_delete_tag(self.project_id, cid, tags=[tag])
        collection = self.syncano.collection_get_one(self.project_id, collection_key=self.collection_key, message_id=1392)
        assert not tag in collection['data']['collection']['tags'], 'Tags didnt delete'
        self.syncano.collection_delete(self.project_id, cid)

    def tearDown(self):
        self.syncano.project_delete(self.project['data']['id'])
        super(TestCollections, self).tearDown()


class TestFolders(SyncanoTest, unittest.TestCase):

    def setUp(self):
        super(TestFolders, self).setUp()
        self.project_name = id_generator()
        self.project = self.syncano.project_new(self.project_name)
        self.project_id = self.project['data']['id']
        self.collection_name = id_generator()
        self.collection_key = id_generator()
        self.collection = self.syncano.collection_new(self.project['data']['id'],
                                                    self.collection_name, self.collection_key)
        self.collection_id = self.collection['data']['collection']['id']
        self.syncano.collection_activate(self.project['data']['id'],
                                       collection_id=self.collection['data']['collection']['id'])
        self.folder_name = id_generator()

    def test_01_create_get_one_get_delete(self):
        folder = self.syncano.folder_new(self.project['data']['id'], self.folder_name,
                                       collection_id=self.collection_id)
        folder2 = self.syncano.folder_get_one(self.project['data']['id'],
                                            self.folder_name, collection_key=self.collection_key)
        assert folder['data']['folder']['id'] == folder2['data']['folder']['id'], 'Folder not created'
        self.syncano.folder_delete(self.project['data']['id'], self.folder_name,
                                 collection_id=self.collection_id, collection_key=self.collection_key)
        folders = self.syncano.folder_get(self.project['data']['id'], collection_key=self.collection_key, message_id=6)
        for f in folders['data']['folder']:
            assert f['id'] != folder['data']['folder']['id']

    def test_02_update(self):
        new_folder_name = id_generator(10)
        folder = self.syncano.folder_new(self.project_id, self.folder_name, collection_key=self.collection_key)
        updated_folder = self.syncano.folder_update(self.project_id, self.folder_name,
                                                  self.collection_id, self.collection_key, new_name=new_folder_name)
        assert updated_folder['data']['folder']['name'] != folder['data']['folder']['name'], "folder name didn`t change"
        folder = self.syncano.folder_get_one(self.project_id, new_folder_name, self.collection_id)
        assert folder['data']['folder'], "folder not returned"
        self.syncano.folder_delete(self.project_id, new_folder_name, collection_id=self.collection_id,
                                 collection_key=self.collection_key)

    def tearDown(self):
        self.syncano.collection_delete(self.project['data']['id'], collection_key=self.collection_key)
        self.syncano.project_delete(self.project['data']['id'])

        super(TestFolders, self).tearDown()


class TestDataObjects(SyncanoTest, unittest.TestCase):

    def setUp(self):
        super(TestDataObjects, self).setUp()
        self.project_name = id_generator()
        self.project = self.syncano.project_new(self.project_name)
        self.project_id = self.project['data']['id']
        self.collection_name = id_generator()
        self.collection_key = id_generator()
        self.collection = self.syncano.collection_new(self.project['data']['id'],
                                                    self.collection_name, self.collection_key)
        self.collection_id = self.collection['data']['collection']['id']
        self.syncano.collection_activate(self.project['data']['id'],
                                       collection_id=self.collection['data']['collection']['id'])
        self.folder1_name = id_generator()
        self.folder2_name = id_generator()
        self.folder1 = self.syncano.folder_new(self.project_id, self.folder1_name, collection_key=self.collection_key)
        self.folder2 = self.syncano.folder_new(self.project_id, self.folder2_name, collection_key=self.collection_key)


    def test_01_new_get_get_one_delete_count(self):
        dataobj = self.syncano.data_new(self.project_id, self.collection_id,
                                      folder=self.folder1_name, state='Moderated')
        data_id=dataobj['data']['data']['id']
        dataobj = self.syncano.data_get_one(self.project_id, self.collection_id, data_id=data_id)
        count = self.syncano.data_count(self.project_id, self.collection_id, folders=[self.folder1_name])
        assert count['data']['count'] == 1, 'Count doesnt work'
        self.syncano.data_delete(self.project_id, self.collection_id, data_ids=[data_id])
        dataobjects = self.syncano.data_get(self.project_id, self.collection_id, folders=[self.folder1_name])
        assert not any([x['data_id'] == data_id for x in dataobjects['data']['data']]), 'Data object not deleted'
        count = self.syncano.data_count(self.project_id, self.collection_id, folders=[self.folder1_name])
        assert count['data']['count'] == 0, 'Count doesnt work'

    def test_02_add_parent_remove_parent(self):
        data_id = self.syncano.data_new(self.project_id, self.collection_id,
                                      folder=self.folder1_name)['data']['data']['id']
        data_id2 = self.syncano.data_new(self.project_id, self.collection_id,
                                      folder=self.folder1_name)['data']['data']['id']
        self.syncano.data_add_parent(self.project_id, data_id, self.collection_id, parent_id=data_id2)
        self.syncano.data_remove_parent(self.project_id, data_id, self.collection_id, parent_id=data_id2)
        self.syncano.data_delete(self.project_id, self.collection_id, data_ids=[data_id, data_id2])

    def test_03_move(self):
        data_id= self.syncano.data_new(self.project_id, self.collection_id,
                                     folder=self.folder1_name)['data']['data']['id']
        self.syncano.data_move(self.project_id, self.collection_id, data_ids=[data_id], new_folder=self.folder2_name)
        dataobjects2 = self.syncano.data_get(self.project_id, self.collection_id, folders=[self.folder2_name])
        dataobjects = self.syncano.data_get(self.project_id, self.collection_id, folders=[self.folder1_name])
        assert any([x['id'] == data_id for x in dataobjects2['data']['data']]), 'Data object not moved to folder'
        assert not any([x['id'] == data_id for x in dataobjects['data']['data']]), 'Data object not moved to folder2'
        self.syncano.data_delete(self.project_id, self.collection_id, data_ids=[data_id])

    def test_04_update(self):
        title = id_generator()
        title2 = id_generator()
        data= self.syncano.data_new(self.project_id, self.collection_id,
                                  folder=self.folder1_name, title=title)
        data_id = data['data']['data']['id']
        data2 = self.syncano.data_update(self.project_id, collection_id=self.collection_id, data_id=data_id, title=title2)
        assert data['data']['data']['title'] != data2['data']['data']['title'], 'title didn`t change'
        self.syncano.data_delete(self.project_id, self.collection_id, data_ids=[data_id])


    def tearDown(self):
        self.syncano.folder_delete(self.project_id, self.folder1_name, collection_id=self.collection_id,
                                     collection_key=self.collection_key)
        self.syncano.folder_delete(self.project_id, self.folder2_name, collection_id=self.collection_id,
                                 collection_key=self.collection_key)
        self.syncano.collection_delete(self.project['data']['id'], collection_key=self.collection_key)
        self.syncano.project_delete(self.project['data']['id'])
        super(TestDataObjects, self).tearDown()


class TestUsers(SyncanoTest, unittest.TestCase):

    def test_01_new_delete_get_all_get_one(self):
        name = id_generator()
        user = self.syncano.user_new(name, nick=id_generator())
        user2 = self.syncano.user_get_one(user_name=name)
        users = self.syncano.user_get_all()
        assert any([x['name'] == name for x in users['data']['user']]), 'User not exists'
        self.syncano.user_delete(str(user['data']['user']['id']))
        users = self.syncano.user_get_all()
        assert not any([x['name'] == name for x in users['data']['user']]), 'User not deleted'

    def test_02_update(self):
        name = id_generator()
        name2 = id_generator()
        user = self.syncano.user_new(name)
        user2 = self.syncano.user_update(user_name=name, nick=name2)
        assert user['data']['user']['id'] == user2['data']['user']['id'], "Updated user has other id"
        assert name2 == user2['data']['user']['nick'], "Nick didnt change"
        self.syncano.user_delete(user_name=user['data']['user']['name'])

    def test_03_count(self):
        name = id_generator()
        count_start = self.syncano.user_count()['data']['count']
        user = self.syncano.user_new(name)
        count = self.syncano.user_count()
        assert count['data']['count'] == count_start + 1, "Counter do not increment after adding user"
        self.syncano.user_delete(user_name=user['data']['user']['name'])
        count = self.syncano.user_count()
        assert count['data']['count'] == count_start, "count do not decrement after delete"

    def test_04_get(self):
        name = id_generator()
        user = self.syncano.user_new(name)
        self.project_name = id_generator()
        self.project = self.syncano.project_new(self.project_name)
        self.project_id = self.project['data']['id']
        self.collection_name = id_generator()
        self.collection_key = id_generator()
        self.collection = self.syncano.collection_new(self.project['data']['id'],
                                                    self.collection_name, self.collection_key)
        self.collection_id = self.collection['data']['collection']['id']
        self.syncano.collection_activate(self.project['data']['id'],
                                       collection_id=self.collection['data']['collection']['id'])
        self.folder1_name = id_generator()
        self.folder1 = self.syncano.folder_new(self.project_id, self.folder1_name, collection_key=self.collection_key)
        dataobj = self.syncano.data_new(self.project_id, self.collection_id,
                                      folder=self.folder1_name, user_name=name)
        users = self.syncano.user_get(self.project_id, self.collection_id, folders=[self.folder1_name])
        assert any([x['name'] == name for x in users['data']['user']]), 'Cant get user by folder'
        self.syncano.data_delete(self.project_id, self.collection_id, data_ids=[dataobj['data']['data']['id']])
        self.syncano.folder_delete(self.project_id, self.folder1_name, self.collection_id, self.collection_key)
        self.syncano.collection_delete(self.project_id, self.collection_id)
        self.syncano.project_delete(self.project_id)
        self.syncano.user.delete(user_id=user['data']['user']['id'])


class TestNotifications(SyncanoTest, unittest.TestCase):

    def setUp(self):
        super(TestNotifications, self).setUp()
        client_name = id_generator(15)
        self.client = self.syncano.client_new(client_name, client_name)

    def test_01_notification_send(self):
        message = id_generator()
        with SyncanoAsyncApi(testconfig.INSTANCE, login=self.client['data']['client']['login'],
                      password=self.client['data']['client']['login'], host=testconfig.HOST) as syncano2:
            self.syncano.notification_send(self.client['data']['client']['id'], uuid=syncano2.cli.uuid, custom_message=message)
            for i in range(10):
                msg = syncano2.get_message(blocking=False)
                if 'data' in msg and 'custom_message' in  msg['data']:
                    assert message == msg['data']['custom_message'], 'Custom message is not the same'
                    break
            else:
                assert 1, 'Couldnt get the message in reasonable time'

    def test_02_notification_history_get_collection_history(self):
        self.project_name = id_generator()
        self.project = self.syncano.project_new(self.project_name)
        self.project_id = self.project['data']['id']
        collection_name = id_generator()
        collection_key = id_generator()
        collection = self.syncano.collection_new(self.project_id, collection_name, collection_key)
        self.syncano.notification_get_collection_history(self.project_id, collection['data']['collection']['id'])
        self.syncano.notification_get_history()
        self.syncano.collection_delete(self.project_id, collection['data']['collection']['id'])
        self.syncano.project_delete(self.project_id)

    def tearDown(self):
        self.syncano.client_delete(self.client['data']['client']['id'])
        super(TestNotifications, self).tearDown()


class TestSubscriptions(SyncanoTest, unittest.TestCase):

    def setUp(self):
        super(TestSubscriptions, self).setUp()
        self.project_name = id_generator()
        self.project = self.syncano.project_new(self.project_name)
        self.project_id = self.project['data']['id']
        self.collection_name = id_generator()
        self.collection_key = id_generator()
        self.collection = self.syncano.collection_new(self.project['data']['id'],
                                                    self.collection_name, self.collection_key)
        self.collection_id = self.collection['data']['collection']['id']
        self.syncano.collection_activate(self.project['data']['id'],
                                       collection_id=self.collection['data']['collection']['id'])

    def test_01_subscribe_unsubscribe_projectget(self):
        self.syncano.subscription_subscribe_project(self.project_id)
        subs = self.syncano.subscription_get()
        assert any([x['type'] == 'Project' and x['id'] == self.project_id for x in subs['data']['subscription']]),\
            "No sub"
        self.syncano.subscription_unsubscribe_project(self.project_id)
        subs = self.syncano.subscription_get()
        assert not any([x['type'] == 'Project' and x['id'] == self.project_id for x in subs['data']['subscription']]),\
            "sub not deleted"

    def test_02_subscribe_unsubscribe_collection(self):
        self.syncano.subscription_subscribe_collection(self.project_id, self.collection_id)
        subs = self.syncano.subscription_get()
        assert any([x['type'] == 'Collection' and x['id'] == self.collection_id\
                    for x in subs['data']['subscription']]), "No sub"
        self.syncano.subscription_unsubscribe_collection(self.project_id, self.collection_id)
        subs = self.syncano.subscription_get()
        assert not any([x['type'] == 'Collection' and x['id'] == self.collection_id\
                        for x in subs['data']['subscription']]), "sub not deleted"

    def tearDown(self):
        self.syncano.collection_delete(self.project_id, self.collection_id)
        self.syncano.project_delete(self.project_id)
        super(TestSubscriptions, self).tearDown()


if __name__ == '__main__':
    suite = unittest.TestSuite()
    for t in (TestInstanceClients, TestDataObjects, TestProjects, TestFolders, TestNotifications,
              TestUsers, TestSubscriptions, TestCollections):
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(t))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    exit(len(result.errors) or len(result.failures))




