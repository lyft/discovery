from .. import settings
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, UTCDateTimeAttribute, JSONAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection


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

    service = UnicodeAttribute(hash_key=True)
    ip_address = UnicodeAttribute(range_key=True)
    service_repo_name_index = ServiceRepoNameIndex()
    service_repo_name = UnicodeAttribute(null=True)
    port = NumberAttribute()
    last_check_in = UTCDateTimeAttribute()
    revision = UnicodeAttribute()
    tags = JSONAttribute()
