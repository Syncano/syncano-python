# -*- coding: utf-8 -*-
import os
import random
import unittest

import syncano


class RegistrationTest(unittest.TestCase):

    def test_register(self):
        connection = syncano.connect(
            host=os.getenv('INTEGRATION_API_ROOT'),
        )

        email = 'syncano.bot+997999{}@syncano.com'.format(random.randint(100000, 50000000))

        connection.connection().register(
            email=email,
            password='test11',
            first_name='Jan',
            last_name='Nowak'
        )

        # test if LIB has a key now;
        account_info = connection.connection().get_account_info()
        self.assertIn('email', account_info)
        self.assertEqual(account_info['email'], email)
