import unittest
from flask import Flask
from flask.ext.cache import Cache
import discovery
from discovery.app.models import Host
from discovery.app.resources.api import RepoRegistration, Registration, BackendSelector
from mock import patch, Mock


class ApiResourceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.cache = Cache(self.app, config={'CACHE_TYPE': 'simple'})
        self.app.cache.clear()
        self.app_context = self.app.app_context()
        self.app_context.push()
        for item in Host.scan():
            item.delete()

    def tearDown(self):
        self.app.cache.clear()
        self.app_context.pop()

    def generate_valid_params(self, param, default):
        if param == 'ip':
            return '10.10.10.10'
        if param == 'service_repo_name':
            return 'bar'
        if param == 'port':
            return 1000
        if param == 'revision':
            return 'bjkc7y8cebyyuide2uincbyu'
        if param == 'tags':
            return '{"az":"foo", "instance_id":"bar", "region":"baz"}'

    def test_get_no_hosts(self):
        registration = Registration()
        response, response_code = registration.get('foo')
        expected = {
            "hosts": [],
            "service": "foo",
            "env": "development"
        }
        assert response_code == 200
        assert response == expected

    @patch('discovery.app.services.host.HostService.list')
    def test_get_with_hosts(self, get_hosts):
        expected_hosts = [
            {
                'service': 'foo',
                'ip_address': '10.10.10.10',
                'service_repo_name': 'bar',
                'port': 10,
                'revision': 'blah',
                'last_check_in': 'timestamp',
                'tags': {
                    'az': 'woot',
                    'instance_id': 'wooooooooot'
                }
            },
            {
                'service': 'foo',
                'ip_address': '11.11.11.11',
                'service_repo_name': None,
                'port': 11,
                'revision': 'blah',
                'last_check_in': 'timestamp2',
                'tags': {
                    'az': 'woot',
                    'instance_id': 'wooooooooot'
                }
            },
        ]
        get_hosts.return_value = expected_hosts
        registration = Registration()
        registration._get_param = Mock(side_effect=self.generate_valid_params)
        response, response_code = registration.get('foo')
        expected = {
            "hosts": expected_hosts,
            "service": "foo",
            "env": "development"
        }
        assert response_code == 200
        assert response == expected

    def test_get_service_repo_name_no_hosts(self):
        registration = RepoRegistration()
        response, response_code = registration.get('foo')
        expected = {
            "hosts": [],
            "service_repo_name": "foo",
            "env": "development"
        }
        assert response_code == 200
        assert response == expected

    @patch('discovery.app.services.host.HostService.list_by_service_repo_name')
    def test_get_service_repo_name_with_hosts(self, get_hosts):
        expected_hosts = [
            {
                'service': 'foo',
                'ip_address': '10.10.10.10',
                'service_repo_name': 'bar',
                'port': 10,
                'revision': 'blah',
                'last_check_in': 'timestamp',
                'tags': {
                    'az': 'woot',
                    'instance_id': 'wooooooooot'
                }
            },
            {
                'service': 'foobaz',
                'service_repo_name': 'bar',
                'ip_address': '11.11.11.11',
                'port': 11,
                'revision': 'blah',
                'last_check_in': 'timestamp2',
                'tags': {
                    'az': 'woot',
                    'instance_id': 'wooooooooot'
                }
            },
        ]
        service_repo_name = 'bar'
        get_hosts.return_value = expected_hosts
        registration = RepoRegistration()
        registration._get_param = Mock(side_effect=self.generate_valid_params)
        response, response_code = registration.get(service_repo_name)
        expected = {
            "hosts": expected_hosts,
            "service_repo_name": service_repo_name,
            "env": "development"
        }
        assert response_code == 200
        assert response == expected

    @patch('discovery.app.resources.api.Registration._get_param')
    def test_post_invalid_params(self, get_param):
        get_param.return_value = '0'
        registration = Registration()
        response, response_code = registration.post('foo')
        expected = {}

        assert response_code == 400
        assert response == expected

    def test_post_valid_params(self):
        registration = Registration()
        registration._get_param = Mock(side_effect=self.generate_valid_params)
        response, response_code = registration.post('foo')
        expected = {}

        assert response_code == 200
        assert response == expected

    def test_delete_nonexistent_host(self):
        registration = Registration()
        response, response_code = registration.delete('foo', '1.1.1.1')

        assert response_code == 400
        assert response == {}

    def test_delete_nonexistent_missing_ip_address(self):
        registration = Registration()
        response, response_code = registration.delete('foo', None)

        assert response_code == 400
        assert response == {}

    def test_delete_invalid_ip_address(self):
        registration = Registration()
        response, response_code = registration.delete('foo', 'bar')

        assert response_code == 400
        assert response == {}

    def test_delete_success(self):
        registration = Registration()
        registration._get_param = Mock(side_effect=self.generate_valid_params)
        registration.post('foo')
        response, response_code = registration.delete('foo', '10.10.10.10')

        assert response_code == 200
        assert response == {}


class BackendSelectorTestCase(unittest.TestCase):

    @patch.object(BackendSelector, 'get_storage')
    def test_backend_selector_select_method_returns_DynamoDB_storage(self, mock_get_storage):
        expected_backend_class = discovery.app.services.query.DynamoQueryBackend
        mock_get_storage.return_value = 'DynamoDB'
        backend_class_instance = BackendSelector().select()
        self.assertTrue(isinstance(backend_class_instance, expected_backend_class))

    @patch.object(BackendSelector, 'get_storage')
    def test_backend_selector_select_method_returns_InMemory_storage(self, mock_get_storage):
        expected_backend_class = discovery.app.services.query.MemoryQueryBackend
        mock_get_storage.return_value = 'InMemory'
        backend_class_instance = BackendSelector().select()
        self.assertTrue(isinstance(backend_class_instance, expected_backend_class))

    @patch.object(BackendSelector, 'get_storage')
    def test_backend_selector_select_method_returns_InFile_storage(self, mock_get_storage):
        expected_backend_class = discovery.app.services.query.LocalFileQueryBackend
        mock_get_storage.return_value = 'InFile'
        backend_class_instance = BackendSelector().select()
        self.assertTrue(isinstance(backend_class_instance, expected_backend_class))

    @patch.object(BackendSelector, 'get_storage')
    def test_assemble_plugin_backend_location_returns_expected_string(self, mock_get_storage):
        expected = 'plugins.HBase.app.services.query'
        mock_get_storage.return_value = 'HBase'
        actual = BackendSelector().assemble_plugin_backend_location()
        self.assertEqual(expected, actual)

    @patch.object(BackendSelector, 'get_storage')
    def test_assemble_plugin_backend_class_name_returns_expected_string(self, mock_get_storage):
        expected = 'HBaseQueryBackend'
        mock_get_storage.return_value = 'HBase'
        actual = BackendSelector().assemble_plugin_backend_class_name()
        self.assertEqual(expected, actual)

    @patch.object(BackendSelector, 'plugins_exist')
    @patch.object(BackendSelector, 'get_query_plugin_from_location_and_name')
    @patch.object(BackendSelector, 'assemble_plugin_backend_class_name')
    @patch.object(BackendSelector, 'assemble_plugin_backend_location')
    @patch.object(BackendSelector, 'get_storage')
    def test_get_query_plugin_from_location_and_name_called_with_expected_args(
            self,
            mock_get_storage,
            mock_assemble_location,
            mock_assemble_class_name,
            mock_get_query_plugin,
            mock_plugins_exist,
    ):
        mock_get_storage.return_value = 'HBase'
        mock_assemble_location.return_value = 'plugins.HBase.app.services.query'
        mock_assemble_class_name.return_value = 'HBaseQueryBackend'
        mock_plugins_exist.return_value = True
        BackendSelector().select()
        mock_get_query_plugin.assert_called_with(
            mock_assemble_location.return_value, mock_assemble_class_name.return_value,
        )
