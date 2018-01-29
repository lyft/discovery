from os import getenv
from collections import namedtuple


defaults = {
    'APPLICATION_DIR': '/srv/service/current',
    # This is used for specific setup in development vs production.
    'APPLICATION_ENV': 'development',
    'DEBUG': True,
    'LOG_LEVEL': 'DEBUG',
    'PORT': 8080,
    # Used only in case of DynamoDB backend.
    'DYNAMODB_TABLE_HOSTS': '',
    # Used only for development in case of DynamoDB backend running locally.
    'DYNAMODB_URL': '',
    # Only applied when DynamoDB backend is used. Create sample DynamoDB table for testing.
    'DYNAMODB_CREATE_TABLES_IN_APP': '',
    # Sweep host (remove from discovery service and backend storage)
    # if the last heartbeat was not performed in last HOST_TTL seconds.
    'HOST_TTL': 600,  # 10 minutes.
    # Keep data cached in discovery service during CACHE_TTL seconds,
    # otherwise call backend storage for data.
    'CACHE_TTL': 30,  # 30 seconds.
    # Supported values: DynamoDB, InMemory, InFile.
    'BACKEND_STORAGE': 'DynamoDB',
    # Flask cache type, null means no caching.
    'CACHE_TYPE': 'null'
}

values = {}
for name, value in defaults.items():
    if isinstance(value, bool):
        values[name] = bool(getenv(name, value))
    elif isinstance(value, int):
        values[name] = int(getenv(name, value))
    elif isinstance(value, basestring):
        values[name] = getenv(name, value)

value = namedtuple('Settings', values.keys())(**values)
