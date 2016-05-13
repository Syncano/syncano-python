import logging
import os

__title__ = 'Syncano Python'
__version__ = '5.1.0'
__author__ = "Daniel Kopka, Michal Kobus, and Sebastian Opalczynski"
__credits__ = ["Daniel Kopka",
               "Michal Kobus",
               "Sebastian Opalczynski"]
__copyright__ = 'Copyright 2015 Syncano'
__license__ = 'MIT'

env_loglevel = os.getenv('SYNCANO_LOGLEVEL', 'INFO')
loglevel = getattr(logging, env_loglevel.upper(), None)

if not isinstance(loglevel, int):
    raise ValueError('Invalid log level: {0}.'.format(loglevel))

console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)

logger = logging.getLogger('syncano')
logger.setLevel(loglevel)
logger.addHandler(console_handler)

# Few global env variables
VERSION = __version__
DEBUG = env_loglevel.lower() == 'debug'
API_ROOT = os.getenv('SYNCANO_APIROOT', 'https://api.syncano.io/')
EMAIL = os.getenv('SYNCANO_EMAIL')
PASSWORD = os.getenv('SYNCANO_PASSWORD')
APIKEY = os.getenv('SYNCANO_APIKEY')
INSTANCE = os.getenv('SYNCANO_INSTANCE')
PUSH_ENV = os.getenv('SYNCANO_PUSH_ENV', 'production')


def connect(*args, **kwargs):
    """
    Connects to Syncano API.

    :type email: string
    :param email: Your Syncano account email address

    :type password: string
    :param password: Your Syncano password

    :type api_key: string
    :param api_key: Your Syncano account key or instance api_key

    :type username: string
    :param username: Instance user name

    :type user_key: string
    :param user_key: Instance user key

    :type instance_name: string
    :param instance_name: Your Syncano instance_name

    :type verify_ssl: boolean
    :param verify_ssl: Verify SSL certificate

    :rtype: :class:`syncano.models.registry.Registry`
    :return: A models registry

    Usage::

        # Admin login
        connection = syncano.connect(email='', password='')
        # OR
        connection = syncano.connect(api_key='')
        # OR
        connection = syncano.connect(social_backend='github', token='sfdsdfsdf')

        # User login
        connection = syncano.connect(username='', password='', api_key='', instance_name='')
        # OR
        connection = syncano.connect(user_key='', api_key='', instance_name='')
    """
    from syncano.connection import DefaultConnection
    from syncano.models import registry

    registry.set_default_connection(DefaultConnection())
    registry.connection.open(*args, **kwargs)
    instance = kwargs.get('instance_name', INSTANCE)

    if instance is not None:
        registry.set_used_instance(instance)
    return registry
