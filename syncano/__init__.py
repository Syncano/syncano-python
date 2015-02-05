import logging
import os

__title__ = 'Syncano Python'
__version__ = '4.0.0'
__author__ = 'Daniel Kopka'
__license__ = 'MIT'
__copyright__ = 'Copyright 2015 Syncano'

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
API_ROOT = os.getenv('SYNCANO_APIROOT', 'https://v4.hydraengine.com/')
EMAIL = os.getenv('SYNCANO_EMAIL', None)
PASSWORD = os.getenv('SYNCANO_PASSWORD', None)
APIKEY = os.getenv('SYNCANO_APIKEY', None)
INSTANCE = os.getenv('SYNCANO_INSTANCE', None)


def connect(*args, **kwargs):
    """
    Connect to Syncano API.
    Usage:
        connection = syncano.connect(email='', password='')
        connection = syncano.connect(api_key='')
    """
    from syncano.connection import default_connection
    from syncano.models import registry

    default_connection.open(*args, **kwargs)
    if INSTANCE:
        registry.set_default_instance(INSTANCE)
    return registry


def connect_instance(name=None, *args, **kwargs):
    """
    Connects with Syncano API and tries to load instance with provided name.
    Usage:
        connection = syncano.connect_instancet('insatce name', email='', password='')
        connection = syncano.connect_instancet('insatce name', api_key='')
    """
    name = name or INSTANCE
    connection = connect(*args, **kwargs)
    return connection.Instance.please.get(name)
