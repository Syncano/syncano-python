import os

from syncano.connection import Connection

from integration_test import IntegrationTest


class LoginTest(IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(LoginTest, cls).setUpClass()

        cls.INSTANCE_NAME = os.getenv('INTEGRATION_INSTANCE_NAME')
        cls.USER_NAME = os.getenv('INTEGRATION_USER_NAME')
        cls.USER_PASSWORD = os.getenv('INTEGRATION_USER_PASSWORD')
        cls.CLASS_NAME = cls.INSTANCE_NAME

        instance = cls.connection.Instance.please.create(name=cls.INSTANCE_NAME)
        api_key = instance.api_keys.create(allow_user_create=True,
                                           ignore_acl=True)

        user = instance.users.create(username=cls.USER_NAME,
                                     password=cls.USER_PASSWORD)

        instance.classes.create(name=cls.CLASS_NAME,
                                schema='[{"name":"obj","type":"string"}]')

        cls.USER_KEY = user.user_key
        cls.USER_API_KEY = api_key.api_key

    @classmethod
    def tearDownClass(cls):
        cls.connection.Instance.please.delete(name=cls.INSTANCE_NAME)
        cls.connection = None

    def check_connection(self, con):
        response = con.request('GET', '/v1/instances/test_login/classes/')

        obj_list = response['objects']

        self.assertEqual(len(obj_list), 2)
        self.assertItemsEqual([o['name'] for o in obj_list], ['user_profile', self.CLASS_NAME])

    def test_admin_login(self):
        con = Connection(host=self.API_ROOT,
                         email=self.API_EMAIL,
                         password=self.API_PASSWORD)
        self.check_connection(con)

    def test_admin_alt_login(self):
        con = Connection(host=self.API_ROOT,
                         api_key=self.API_KEY)
        self.check_connection(con)

    def test_user_login(self):
        con = Connection(host=self.API_ROOT,
                         username=self.USER_NAME,
                         password=self.USER_PASSWORD,
                         api_key=self.API_KEY,
                         instance_name=self.INSTANCE_NAME)
        self.check_connection(con)

    def test_user_alt_login(self):
        con = Connection(host=self.API_ROOT,
                         api_key=self.USER_API_KEY,
                         user_key=self.USER_KEY,
                         instance_name=self.INSTANCE_NAME)
        self.check_connection(con)
