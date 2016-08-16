import unittest
import json

from discovery import app
from discovery.app.models.host import Host


class FlaskResourceTestCase(unittest.TestCase):
    def setUp(self):
        self.debug = app.app.debug
        app.app.debug = True
        self.client = app.app.test_client()
        for item in Host.scan():
            item.delete()

    def tearDown(self):
        app.debug = self.debug

    @staticmethod
    def _generate_registration_data(ip, lb_weight=None):
        tags = {"az": "foo", "instance_id": "bar", "region": "baz"}
        if lb_weight:
            tags['load_balancing_weight'] = lb_weight
        return {
            'ip': ip,
            'service_repo_name': 'bar',
            'port': 1000,
            'revision': 'bjkc7y8cebyyuide2uincbyu',
            'tags': json.dumps(tags),
        }

    def assert_one_host_with_load_balancing_weight(self, weight):
        hosts = list(Host.scan())
        self.assertEquals(1, len(hosts))
        self.assertEquals(weight, hosts[0].tags['load_balancing_weight'])

    def test_post_explicit_ip(self):
        response = self.client.post(
            '/v1/registration/myservice',
            data={
                'ip': '10.10.10.10',
                'service_repo_name': 'bar',
                'port': 1000,
                'revision': 'bjkc7y8cebyyuide2uincbyu',
                'tags': '{"az":"foo", "instance_id":"bar", "region":"baz"}',
            },
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'X-FORWARDED-FOR': '192.168.216.186'}
        )
        self.assertEquals(200, response.status_code)
        hosts = list(Host.scan())
        self.assertEquals(1, len(hosts))
        self.assertEquals('10.10.10.10', hosts[0].ip_address)

    def test_post_auto_ip_one_hop(self):
        response = self.client.post(
            '/v1/registration/myservice',
            data={
                'auto_ip': True,
                'service_repo_name': 'bar',
                'port': 1000,
                'revision': 'bjkc7y8cebyyuide2uincbyu',
                'tags': '{"az":"foo", "instance_id":"bar", "region":"baz"}',
            },
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'HTTP_X_FORWARDED_FOR': '192.168.216.186'}
        )
        self.assertEquals(200, response.status_code)
        hosts = list(Host.scan())
        self.assertEquals(1, len(hosts))
        self.assertEquals('192.168.216.186', hosts[0].ip_address)

    def test_post_auto_ip_out_of_range_1(self):
        response = self.client.post(
            '/v1/registration/myservice',
            data={
                'auto_ip': True,
                'service_repo_name': 'bar',
                'port': 1000,
                'revision': 'bjkc7y8cebyyuide2uincbyu',
                'tags': '{"az":"foo", "instance_id":"bar", "region":"baz"}',
            },
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'HTTP_X_FORWARDED_FOR': '0.168.216.186'}
        )
        self.assertEquals(400, response.status_code)

    def test_post_auto_ip_out_of_range_2(self):
        response = self.client.post(
            '/v1/registration/myservice',
            data={
                'auto_ip': True,
                'service_repo_name': 'bar',
                'port': 1000,
                'revision': 'bjkc7y8cebyyuide2uincbyu',
                'tags': '{"az":"foo", "instance_id":"bar", "region":"baz"}',
            },
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'HTTP_X_FORWARDED_FOR': '192.169.216.186'}
        )
        self.assertEquals(400, response.status_code)

    def test_post_auto_ip_out_of_range_3(self):
        response = self.client.post(
            '/v1/registration/myservice',
            data={
                'auto_ip': True,
                'service_repo_name': 'bar',
                'port': 1000,
                'revision': 'bjkc7y8cebyyuide2uincbyu',
                'tags': '{"az":"foo", "instance_id":"bar", "region":"baz"}',
            },
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'HTTP_X_FORWARDED_FOR': '192.168.256.186'}
        )
        self.assertEquals(400, response.status_code)

    def test_post_auto_ip_out_of_range_4(self):
        response = self.client.post(
            '/v1/registration/myservice',
            data={
                'auto_ip': True,
                'service_repo_name': 'bar',
                'port': 1000,
                'revision': 'bjkc7y8cebyyuide2uincbyu',
                'tags': '{"az":"foo", "instance_id":"bar", "region":"baz"}',
            },
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'HTTP_X_FORWARDED_FOR': '192.168.216.256'}
        )
        self.assertEquals(400, response.status_code)

    def test_post_auto_ip_two_hops_picks_last(self):
        response = self.client.post(
            '/v1/registration/myservice',
            data={
                'auto_ip': True,
                'service_repo_name': 'bar',
                'port': 1000,
                'revision': 'bjkc7y8cebyyuide2uincbyu',
                'tags': '{"az":"foo", "instance_id":"bar", "region":"baz"}',
            },
            environ_base={
                'REMOTE_ADDR': '127.0.0.1',
                'HTTP_X_FORWARDED_FOR': '192.168.0.0,192.168.216.186',
            }
        )
        self.assertEquals(200, response.status_code)
        hosts = list(Host.scan())
        self.assertEquals(1, len(hosts))
        self.assertEquals('192.168.216.186', hosts[0].ip_address)

    def test_post_invalid_neither_ip(self):
        response = self.client.post(
            '/v1/registration/myservice',
            data={
                'service_repo_name': 'bar',
                'port': 1000,
                'revision': 'bjkc7y8cebyyuide2uincbyu',
                'tags': '{"az":"foo", "instance_id":"bar", "region":"baz"}',
            },
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'HTTP_X_FORWARDED_FOR': '192.168.216.186'}
        )
        self.assertEquals(400, response.status_code)

    def test_loadbalancing_set_weight(self):
        post_response = self.client.post(
            '/v1/registration/myservice',
            data=self._generate_registration_data('10.10.10.10'),
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'X-FORWARDED-FOR': '192.168.216.186'}
        )
        self.assertEquals(200, post_response.status_code)

        loadbalancing_response = self.client.post(
            '/v1/loadbalancing/myservice/10.10.10.10',
            data={'load_balancing_weight': '10'}
        )
        self.assertEquals(204, loadbalancing_response.status_code)
        self.assert_one_host_with_load_balancing_weight(10)

        # Tag should remain after subsequent host registrations
        post_response = self.client.post(
            '/v1/registration/myservice',
            data=self._generate_registration_data('10.10.10.10'),
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'X-FORWARDED-FOR': '192.168.216.186'}
        )
        self.assertEquals(200, post_response.status_code)
        self.assert_one_host_with_load_balancing_weight(10)

    def test_registration_get_load_balancing_weight(self):
        post_response = self.client.post(
            '/v1/registration/myservice',
            data=self._generate_registration_data('10.10.10.10'),
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'X-FORWARDED-FOR': '192.168.216.186'}
        )
        self.assertEquals(200, post_response.status_code)

        loadbalancing_response = self.client.post(
            '/v1/loadbalancing/myservice/10.10.10.10',
            data={'load_balancing_weight': '10'}
        )
        self.assertEquals(204, loadbalancing_response.status_code)

        get_response = self.client.get('/v1/registration/myservice')
        self.assertEquals(200, get_response.status_code)

        get_data = json.loads(get_response.data)
        self.assertEquals(1, len(get_data['hosts']))
        self.assertEquals(10, (get_data['hosts'][0]['tags']
                               ['load_balancing_weight']))

    def test_loadbalancing_update_weight(self):
        post_response = self.client.post(
            '/v1/registration/myservice',
            data=self._generate_registration_data('10.10.10.10', lb_weight=10),
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'X-FORWARDED-FOR': '192.168.216.186'}
        )
        self.assertEquals(200, post_response.status_code)

        loadbalancing_response = self.client.post(
            '/v1/loadbalancing/myservice/10.10.10.10',
            data={'load_balancing_weight': '50'}
        )
        self.assertEquals(204, loadbalancing_response.status_code)

    def test_loadbalancing_update_all_weight(self):
        post1_response = self.client.post(
            '/v1/registration/myservice',
            data=self._generate_registration_data('10.10.10.10', lb_weight=10),
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'X-FORWARDED-FOR': '192.168.216.186'}
        )
        self.assertEquals(200, post1_response.status_code)
        post2_response = self.client.post(
            '/v1/registration/myservice',
            data=self._generate_registration_data('10.10.10.11', lb_weight=10),
            environ_base={'REMOTE_ADDR': '127.0.0.1',
                          'X-FORWARDED-FOR': '192.168.216.186'}
        )
        self.assertEquals(200, post2_response.status_code)

        loadbalancing_response = self.client.post(
            '/v1/loadbalancing/myservice',
            data={'load_balancing_weight': '50'}
        )
        self.assertEquals(204, loadbalancing_response.status_code)

        hosts = list(Host.scan())
        self.assertEquals(2, len(hosts))
        for host in hosts:
            self.assertEquals(50, host.tags['load_balancing_weight'])

    def test_loadbalancing_invalid_host(self):
        response = self.client.post(
            '/v1/loadbalancing/myservice/10.10.10.10',
            data={'load_balancing_weight': '10'}
        )
        self.assertEquals(404, response.status_code)

    def test_loadbalancing_invalid_weight(self):
        response = self.client.post(
            '/v1/loadbalancing/myservice/10.10.10.10',
            data={'load_balancing_weight': 'not_an_integer'}
        )
        self.assertEquals(400, response.status_code)

    def test_loadbalancing_weight_out_of_range(self):
        response = self.client.post(
            '/v1/loadbalancing/myservice/10.10.10.10',
            data={'load_balancing_weight': '9001'}
        )
        self.assertEquals(400, response.status_code)
