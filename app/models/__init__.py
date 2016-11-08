from .. import settings
from host import Host


if settings.get('DYNAMODB_CREATE_TABLES_IN_APP'):
    if not Host.exists():
        Host.create_table(
            read_capacity_units=5,
            write_capacity_units=10,
            wait=True)
