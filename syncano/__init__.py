import logging
import os

__title__ = 'Syncano Python'
__version__ = '4.0.0'
__author__ = 'Daniel Kopka'
__license__ = 'MIT'
__copyright__ = 'Copyright 2015 Syncano'

VERSION = __version__
API_ROOT = os.getenv('SYNCANO_API_ROOT', 'https://v4.hydraengine.com/')

env_loglevel = os.getenv('SYNCANO_LOGLEVEL', 'INFO')
loglevel = getattr(logging, env_loglevel.upper(), None)

if not isinstance(loglevel, int):
    raise ValueError('Invalid log level: {0}.'.format(loglevel))

DEBUG = env_loglevel.lower() == 'debug'

console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)

logger = logging.getLogger('syncano')
logger.setLevel(loglevel)
logger.addHandler(console_handler)


def connect(*args, **kwargs):
    """
    Connect to Syncano API.
    """
    from syncano.connection import Connection
    return Connection(*args, **kwargs)
