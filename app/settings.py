from os import getenv
from collections import namedtuple


DYNAMODB_TABLE_HOSTS = getenv('DYNAMODB_TABLE_HOSTS')
DYNAMODB_URL = getenv('DYNAMODB_URL')
CACHE_TYPE = getenv('CACHE_TYPE')
DYNAMODB_CREATE_TABLES_IN_APP = getenv('DYNAMODB_CREATE_TABLES_IN_APP')
HOST_TTL = int(getenv('HOST_TTL'))
CACHE_TTL = int(getenv('CACHE_TTL'))

# Checks to make sure the required env values got hydrated.
if DYNAMODB_TABLE_HOSTS is "":
    raise Exception("Required environment variable DYNAMODB_TABLE_HOSTS is missing")


def get(name, default=None):
    """
    Get the value of a variable in the settings module scope.
    """
    return globals().get(name, default)

APPLICATION_ENV = getenv('APPLICATION_ENV', 'development')

defaults = {
    'APPLICATION_DIR': '/srv/service/current',
    'APPLICATION_ENV': 'development',
    'DEBUG': True,
    'LOG_LEVEL': 'DEBUG',
    'SERVER_PORT': 80,
    'PRETEND_MODE': False,
    'DYNAMODB_TABLE_HOSTS': DYNAMODB_TABLE_HOSTS,
    'DYNAMODB_URL': DYNAMODB_URL,
    'DYNAMODB_CREATE_TABLES_IN_APP': DYNAMODB_CREATE_TABLES_IN_APP,
    'HOST_TTL': 600,     # 10 minutes
    'CACHE_TTL': 30
}

values = {}
for name, value in defaults.items():
    if isinstance(value, bool):
        values[name] = bool(getenv(name, value))
    elif isinstance(value, int):
        values[name] = int(getenv(name, value))
    elif isinstance(value, basestring):
        values[name] = getenv(name, value)

settings = namedtuple('Settings', values.keys())(**values)
