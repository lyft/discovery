from .. import settings
from botocore.vendored import requests
from botocore.vendored.requests import adapters
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, UTCDateTimeAttribute, JSONAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection


class CustomPynamoSession(requests.Session):
    def __init__(self):
        super(CustomPynamoSession, self).__init__()
        self.mount('http://', adapters.HTTPAdapter(pool_maxsize=settings.value.CONNECTION_POOL_SIZE))
        self.mount('https://', adapters.HTTPAdapter(pool_maxsize=settings.value.CONNECTION_POOL_SIZE))


class ServiceRepoNameIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
        read_capacity_units = 30
        write_capacity_units = 30
    service_repo_name = UnicodeAttribute(hash_key=True)
    ip_address = UnicodeAttribute(range_key=True)


class Host(Model):
    """
    A DynamoDB Server Host.
    """

    class Meta:
        table_name = settings.value.DYNAMODB_TABLE_HOSTS
        if settings.value.APPLICATION_ENV == 'development':
            host = settings.value.DYNAMODB_URL
        session_cls = CustomPynamoSession

    service = UnicodeAttribute(hash_key=True)
    ip_address = UnicodeAttribute(range_key=True)
    service_repo_name_index = ServiceRepoNameIndex()
    service_repo_name = UnicodeAttribute(null=True)
    port = NumberAttribute()
    last_check_in = UTCDateTimeAttribute()
    revision = UnicodeAttribute()
    tags = JSONAttribute()
