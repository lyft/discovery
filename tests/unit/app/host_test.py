import unittest
from mock import patch, Mock
from flask import Flask
from flask.ext.cache import Cache
from datetime import datetime, timedelta
import os
from discovery.app.services import host


# TODO should also have a class that tests the HostService semantics without
#      relying on mocking the underlying implementation
class DynamoHostServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.cache = Cache(self.app, config={'CACHE_TYPE': 'simple'})
        self.app.cache.clear()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app.cache.clear()
        self.app_context.pop()

    def _generate_valid_tags(self):
        return {'az': 'foo', 'instance_id': 'bar', 'region': 'baz'}

    def _mock_host(self):
        return Mock(spec=['service', 'ip_address', 'service_repo_name', 'port',
                          'revision', 'last_check_in', 'tags', 'save'])

    def _new_host_service(self):
        return host.HostService()

    @patch('discovery.app.models.host.Host.get')
    @patch('discovery.app.models.host.Host.save')
    def test_update_succeeds(self, save, get):
        save.return_value = Mock(spec=bool)
        get.return_value = self._mock_host()
        host = self._new_host_service()
        success = host.update(
            service='foo',
            ip_address='10.10.10.10',
            service_repo_name='bar',
            port=80,
            revision='abc123',
            last_check_in=datetime.utcnow(),
            tags=self._generate_valid_tags()
        )
        assert success is True

    @patch('discovery.app.models.host.Host.get')
    @patch('discovery.app.models.host.Host.save')
    def test_service_repo_name_optional(self, save, get):
        save.return_value = Mock(spec=bool)
        get.return_value = None
        host = self._new_host_service()
        success = host.update(
            service='foo',
            ip_address='10.10.10.10',
            service_repo_name=None,
            port=80,
            revision='abc123',
            last_check_in=datetime.utcnow(),
            tags=self._generate_valid_tags()
        )
        assert success is True

    @patch('discovery.app.models.host.Host.get')
    @patch('discovery.app.models.host.Host.save')
    def test_update_invalid_ip(self, save, get):
        save.return_value = Mock(spec=bool)
        get.return_value = Mock(spec=['port', 'revision', 'last_check_in', 'tags', 'save'])
        host = self._new_host_service()
        success = host.update(
            service='foo',
            ip_address='invalid.ip.address',
            service_repo_name='bar',
            port=80,
            revision='abc123',
            last_check_in=datetime.utcnow(),
            tags=self._generate_valid_tags()
        )
        assert success is False
        success = host.update(
            service='foo',
            ip_address='555.555.555.555',
            service_repo_name='bar',
            port=80,
            revision='abc123',
            last_check_in=datetime.utcnow(),
            tags=self._generate_valid_tags()
        )
        assert success is False

    @patch('discovery.app.models.host.Host.get')
    @patch('discovery.app.models.host.Host.save')
    def test_update_invalid_port(self, save, get):
        save.return_value = Mock(spec=bool)
        get.return_value = Mock(spec=['port', 'revision', 'last_check_in', 'tags', 'save'])
        port = -1
        tags = self._generate_valid_tags()
        host = self._new_host_service()
        success = host.update(
            service='foo',
            ip_address='10.10.10.10',
            service_repo_name='bar',
            port=port,
            revision='abc123',
            last_check_in=datetime.utcnow(),
            tags=tags
        )
        assert success is False

        success = host.update(
            service='foo',
            ip_address='10.10.10.10',
            service_repo_name='bar',
            port='test',
            revision='abc123',
            last_check_in=datetime.utcnow(),
            tags=tags
        )
        assert success is False

    @patch('discovery.app.models.host.Host.get')
    @patch('discovery.app.models.host.Host.save')
    def test_update_invalid_last_check_in(self, save, get):
        save.return_value = Mock(spec=bool)
        get.return_value = Mock(spec=['port', 'revision', 'last_check_in', 'tags', 'save'])
        tags = self._generate_valid_tags()
        host = self._new_host_service()
        success = host.update(
            service='foo',
            ip_address='10.10.10.10',
            service_repo_name='bar',
            port=80,
            revision=None,
            last_check_in=datetime.utcnow(),
            tags=tags
        )
        assert success is False

    @patch('discovery.app.models.host.Host.get')
    @patch('discovery.app.models.host.Host.save')
    def test_update_invalid_tags(self, save, get):
        save.return_value = Mock(spec=bool)
        get.return_value = Mock(spec=['port', 'revision', 'last_check_in', 'tags', 'save'])
        tags = {'invalid_az': 'foo', 'instance_id': 'bar', 'region': 'baz'}
        host = self._new_host_service()
        success = host.update(
            service='foo',
            ip_address='10.10.10.10',
            service_repo_name='bar',
            port=80,
            revision='abc123',
            last_check_in=datetime.utcnow(),
            tags=tags
        )
        assert success is False

        tags = {'az': 'foo', 'invalid_instance_id': 'bar', 'region': 'baz'}
        success = host.update(
            service='foo',
            ip_address='10.10.10.10',
            service_repo_name='bar',
            port=80,
            revision='abc123',
            last_check_in=datetime.utcnow(),
            tags=tags
        )
        assert success is False

        tags = {'az': 'foo', 'instance_id': 'bar', 'invalid_region': 'baz'}
        success = host.update(
            service='foo',
            ip_address='10.10.10.10',
            service_repo_name='bar',
            port=80,
            revision='abc123',
            last_check_in=datetime.utcnow(),
            tags=tags
        )
        assert success is False

    @patch('discovery.app.models.host.Host.query')
    @patch('discovery.app.services.host.HostService._is_expired')
    def test_list(self, expired, query):
        self.app.cache = Cache(self.app, config={'CACHE_TYPE': 'null'})
        service = 'foo'
        query.return_value = []
        expired.return_value = False
        host = self._new_host_service()
        hosts = host.list(service)
        expected = []
        assert hosts == expected

        host1 = type('lamdbaobject', (object,), {})()
        host1.service = service
        host1.ip_address = '10.10.10.10'
        host1.service_repo_name = 'bar'
        host1.port = 80
        host1.revision = 'abc123'
        host1.last_check_in = datetime.utcnow()
        host1.tags = self._generate_valid_tags()
        host2 = type('lamdbaobject', (object,), {})()
        host2.service = service
        host2.ip_address = '10.10.10.11'
        host2.service_repo_name = 'bar'
        host2.port = 80
        host2.revision = 'abc123'
        host2.last_check_in = datetime.utcnow()
        host2.tags = self._generate_valid_tags()
        query.return_value = [
            host1,
            host2
        ]
        host = self._new_host_service()
        hosts = host.list(service)
        expected = [
            {
                'service': host1.service,
                'last_check_in': host1.last_check_in,
                'ip_address': host1.ip_address,
                'service_repo_name': host1.service_repo_name,
                'port': host1.port,
                'revision': host1.revision,
                'tags': host1.tags
            },
            {
                'service': host2.service,
                'last_check_in': host2.last_check_in,
                'ip_address': host2.ip_address,
                'service_repo_name': host2.service_repo_name,
                'port': host2.port,
                'revision': host2.revision,
                'tags': host2.tags
            }
        ]
        assert hosts == expected

    @patch('discovery.app.models.host.Host.service_repo_name_index.query')
    @patch('discovery.app.services.host.HostService._is_expired')
    def test_list_by_service_repo_name(self, expired, query):
        self.app.cache = Cache(self.app, config={'CACHE_TYPE': 'null'})
        service = 'foo'
        service_repo_name = 'bar'
        query.return_value = []
        expired.return_value = False
        host = self._new_host_service()
        hosts = host.list_by_service_repo_name(service_repo_name)
        expected = []
        assert hosts == expected

        host1 = type('lamdbaobject', (object,), {})()
        host1.service = service
        host1.ip_address = '10.10.10.10'
        host1.service_repo_name = 'bar'
        host1.port = 80
        host1.revision = 'abc123'
        host1.last_check_in = datetime.utcnow()
        host1.tags = self._generate_valid_tags()
        host2 = type('lamdbaobject', (object,), {})()
        host2.service = service
        host2.ip_address = '10.10.10.11'
        host2.service_repo_name = 'bar'
        host2.port = 80
        host2.revision = 'abc123'
        host2.last_check_in = datetime.utcnow()
        host2.tags = self._generate_valid_tags()
        query.return_value = [
            host1,
            host2
        ]
        host = self._new_host_service()
        hosts = host.list_by_service_repo_name(service)
        expected = [
            {
                'service': host1.service,
                'last_check_in': host1.last_check_in,
                'ip_address': host1.ip_address,
                'service_repo_name': host1.service_repo_name,
                'port': host1.port,
                'revision': host1.revision,
                'tags': host1.tags
            },
            {
                'service': host2.service,
                'last_check_in': host2.last_check_in,
                'ip_address': host2.ip_address,
                'service_repo_name': host2.service_repo_name,
                'port': host2.port,
                'revision': host2.revision,
                'tags': host2.tags
            }
        ]
        assert hosts == expected

    @patch('discovery.app.services.query.Host.get')
    @patch('discovery.app.services.query.Host.save')
    def test_set_tag(self, save, get):
        host = self._mock_host()
        host.tags = {}

        get.return_value = host

        self._new_host_service().set_tag(
            service='foo',
            ip_address='10.10.10.10',
            tag_name='tagname',
            tag_value='value'
        )

        assert host.tags == {'tagname': 'value'}
        save.assert_called_once()

    @patch('discovery.app.services.query.Host.batch_write')
    @patch('discovery.app.services.query.Host.query')
    def test_set_tag_all(self, query, batch_write):
        host1 = self._mock_host()
        host1.tags = {}
        host2 = self._mock_host()
        host2.tags = {}

        query.return_value = [host1, host2]

        self._new_host_service().set_tag_all(
            service='foo',
            tag_name='tagname',
            tag_value='value'
        )

        assert host1.tags == {'tagname': 'value'}
        assert host2.tags == {'tagname': 'value'}
        batch_write.assert_called_once()

    def noop(self):
        pass

    @patch('discovery.app.models.host.Host.query')
    def test_sweeper(self, query):
        # have query return hosts, some of which are expired
        # verify that the expired hosts are not returned
        service = 'foo'
        host = self._new_host_service()
        host1 = type('lamdbaobject', (object,), {})()
        host1.service = service
        host1.ip_address = '10.10.10.10'
        host1.service_repo_name = 'bar'
        host1.port = 80
        host1.revision = 'abc123'
        host1.last_check_in = datetime.today() - timedelta(days=365)   # this host is expired
        host1.tags = self._generate_valid_tags()
        host1.delete = self.noop
        host2 = type('lamdbaobject', (object,), {})()
        host2.service = service
        host2.ip_address = '10.10.10.11'
        host2.service_repo_name = 'bar'
        host2.port = 80
        host2.revision = 'abc123'
        host2.last_check_in = datetime.utcnow()
        host2.tags = self._generate_valid_tags()
        host2.delete = self.noop

        query.return_value = [
            host1,
            host2
        ]
        hosts = host.list(service)
        expected = [
            {
                'service': host2.service,
                'last_check_in': host2.last_check_in,
                'ip_address': host2.ip_address,
                'service_repo_name': host2.service_repo_name,
                'port': host2.port,
                'revision': host2.revision,
                'tags': host2.tags
            }
        ]
        assert hosts == expected

    def test_is_expired(self):
        host = self._new_host_service()
        host1 = {
            # datetime.utcnow() is used to set last_check_in at registration
            # time so that's what we need to test with
            'last_check_in':  datetime.utcnow() - timedelta(minutes=11),

            # _is_expired method references these host fields...
            'service': 'my_service',
            'tags': {
                'instance_id': 'my_id',
            },
        }

        _environ = dict(os.environ)
        try:
            # set TZ so the results don't depend on local machine's timezone
            os.environ['TZ'] = 'America/Chicago'
            assert host._is_expired(host1) == True
        finally:
            # restore os.environ after test
            os.environ.clear()
            os.environ.update(_environ)
