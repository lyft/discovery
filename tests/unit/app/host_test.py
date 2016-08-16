import unittest
from mock import patch, call, Mock, MagicMock
from flask import Flask
from flask.ext.cache import Cache
from datetime import datetime, timedelta
from discovery.app.services.host import HostService


class HostServiceTestCase(unittest.TestCase):
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

    @patch('discovery.app.models.host.Host.get')
    @patch('discovery.app.models.host.Host.save')
    def test_update_succeeds(self, save, get):
        save.return_value = Mock(spec=bool)
        get.return_value = Mock(spec=['port', 'revision', 'last_check_in', 'tags', 'save'])
        host = HostService()
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

    def test_service_repo_name_optional(self):
        host = HostService()
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
        host = HostService()
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
        host = HostService()
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
        host = HostService()
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
        host = HostService()
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
        host = HostService()
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
        host = HostService()
        hosts = host.list(service)
        expected = [
            {
                'service': host1.service,
                'last_check_in': str(host1.last_check_in),
                'ip_address': host1.ip_address,
                'service_repo_name': host1.service_repo_name,
                'port': host1.port,
                'revision': host1.revision,
                'tags': host1.tags
            },
            {
                'service': host2.service,
                'last_check_in': str(host2.last_check_in),
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
        host = HostService()
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
        host = HostService()
        hosts = host.list_by_service_repo_name(service)
        expected = [
            {
                'service': host1.service,
                'last_check_in': str(host1.last_check_in),
                'ip_address': host1.ip_address,
                'service_repo_name': host1.service_repo_name,
                'port': host1.port,
                'revision': host1.revision,
                'tags': host1.tags
            },
            {
                'service': host2.service,
                'last_check_in': str(host2.last_check_in),
                'ip_address': host2.ip_address,
                'service_repo_name': host2.service_repo_name,
                'port': host2.port,
                'revision': host2.revision,
                'tags': host2.tags
            }
        ]
        assert hosts == expected

    @patch('discovery.app.models.host.Host.get')
    def test_set_tag(self, get):
        host = Mock(spec=['port', 'revision', 'last_check_in', 'tags', 'save'])
        host.save.return_value = Mock(spec=bool)
        host.tags = {}

        get.return_value = host

        HostService().set_tag(
            service='foo',
            ip_address='10.10.10.10',
            tag_name='tagname',
            tag_value='value'
        )

        assert host.tags == {'tagname': 'value'}
        host.save.assert_called_once()

    @patch('discovery.app.models.host.Host.batch_write')
    @patch('discovery.app.models.host.Host.query')
    def test_set_tag_all(self, query, batch_write):
        enter = MagicMock()
        ctx_manager = MagicMock()
        batch_write.return_value = ctx_manager
        ctx_manager.__enter__.return_value = enter

        host1 = Mock(spec=['port', 'revision', 'last_check_in', 'tags', 'save'])
        host1.save.return_value = Mock(spec=bool)
        host1.tags = {}
        host2 = Mock(spec=['port', 'revision', 'last_check_in', 'tags', 'save'])
        host2.save.return_value = Mock(spec=bool)
        host2.tags = {}

        query.return_value = [host1, host2]

        HostService().set_tag_all(
            service='foo',
            tag_name='tagname',
            tag_value='value'
        )

        assert host1.tags == {'tagname': 'value'}
        assert host2.tags == {'tagname': 'value'}
        enter.save.assert_has_calls([call(host1), call(host2)])

    def noop(self):
        pass

    @patch('discovery.app.models.host.Host.query')
    def test_sweeper(self, query):
        # have query return hosts, some of which are expired
        # verify that the expired hosts are not returned
        service = 'foo'
        host = HostService()
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
                'last_check_in': str(host2.last_check_in),
                'ip_address': host2.ip_address,
                'service_repo_name': host2.service_repo_name,
                'port': host2.port,
                'revision': host2.revision,
                'tags': host2.tags
            }
        ]
        assert hosts == expected
