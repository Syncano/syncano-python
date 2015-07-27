import os
import syncano
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
        cls.connection = None

    @classmethod
    def tearDownClass(cls):
        super(LoginTest, cls).setUpClass()

        cls.connection.Instance.please.delete(name=cls.INSTANCE_NAME)
        cls.connection = None

    def check_connection(self, con):
        obj_list = con.Class.please.list(instance_name=self.INSTANCE_NAME)

        self.assertEqual(len(list(obj_list)), 2)
        self.assertItemsEqual([o.name for o in obj_list], ['user_profile', self.CLASS_NAME])

    def test_admin_login(self):
        con = syncano.connect(host=self.API_ROOT,
                              email=self.API_EMAIL,
                              password=self.API_PASSWORD)
        con = self.check_connection(con)

    def test_admin_alt_login(self):
        con = syncano.connect(host=self.API_ROOT,
                              api_key=self.API_KEY)
        con = self.check_connection(con)

    def test_user_login(self):
        con = syncano.connect(host=self.API_ROOT,
                              username=self.USER_NAME,
                              password=self.USER_PASSWORD,
                              user_key=self.USER_KEY,
                              instance_name=self.INSTANCE_NAME)
        con = self.check_connection(con)

    def test_user_alt_login(self):
        con = syncano.connect(host=self.API_ROOT,
                              api_key=self.USER_API_KEY,
                              user_key=self.USER_KEY,
                              instance_name=self.INSTANCE_NAME)
        con = self.check_connection(con)
