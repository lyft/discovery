from os import getenv

defaults = {
    'APPLICATION_DIR': '/srv/service/current',
    # This is used for specific setup for development vs production.
    'APPLICATION_ENV': 'development',
    'DEBUG': True,
    'LOG_LEVEL': 'DEBUG',
    'PORT': 80,
    # Only applied when DynamoDB backend used.
    'DYNAMODB_TABLE_HOSTS': '',
    # Used only for development in case of DynamoDB backed running locally.
    'DYNAMODB_URL': '',
    # Only applied when DynamoDB backedn used. Create sample DynamoDB table for testing.
    'DYNAMODB_CREATE_TABLES_IN_APP': '',
    'HOST_TTL': 600,  # 10 minutes.
    'CACHE_TTL': 30,  # 30 seconds.
    # Supported values: DynamoDB, InMemory, InFile.
    'BACKEND_STORAGE': 'DynamoDB',
    # Flask cache type, empty means no caching.
    'CACHE_TYPE': ''
}

values = {}
for name, value in defaults.items():
    if isinstance(value, bool):
        values[name] = bool(getenv(name, value))
    elif isinstance(value, int):
        values[name] = int(getenv(name, value))
    elif isinstance(value, basestring):
        values[name] = getenv(name, value)


def get(name):
    '''
    Get environment variable or default value from the defaults if env variable
    is not set.
    '''

    return values.get(name)
