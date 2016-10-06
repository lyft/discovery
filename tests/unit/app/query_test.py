import abc
import unittest
from datetime import datetime
from discovery.app.services import query


class QueryBackendTestCase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _new_query_backend(self):
        pass

    def _generate_valid_tags(self):
        return {'az': 'foo', 'instance_id': 'bar', 'region': 'baz'}

    def test_basic_operations(self):
        query = self._new_query_backend()
        self.assertEqual([], list(query.query('wut')))

        host1 = {
            'service': 'host1',
            'ip_address': '1.1.1.1',
            'service_repo_name': 'hosts_repo',
            'port': 80,
            'revision': 'host1_rev1',
            'last_check_in': datetime.utcnow(),
            'tags': self._generate_valid_tags()
        }

        host2 = {
            'service': 'host2',
            'ip_address': '1.1.1.1',
            'service_repo_name': host1['service_repo_name'],
            'port': 90,
            'revision': 'host2_rev1',
            'last_check_in': datetime.utcnow(),
            'tags': self._generate_valid_tags()
        }

        query.put(host1)

        host1_get = query.get(host1['service'], host1['ip_address'])
        self.assertEqual(host1, host1_get)

        query.put(host2)

        host1_get = query.get(host1['service'], host1['ip_address'])
        self.assertEqual(host1, host1_get)

        host2_get = query.get(host2['service'], host2['ip_address'])
        self.assertEqual(host2, host2_get)

        host2_service = host2['service']
        host2['service'] = 'bad!!!!'

        self.assertNotEqual(host2, host2_get)

        host2['service'] = host2_service
        self.assertEqual(host2, host2_get)

        secondary_query = sorted(query.query_secondary_index(host1['service_repo_name']))
        self.assertEqual([host1, host2], secondary_query)

        query.delete(host2['service'], host2['ip_address'])

        secondary_query = sorted(query.query_secondary_index(host1['service_repo_name']))
        self.assertEqual([host1], secondary_query)

        self.assertIsNone(query.get(host2['service'], host2['ip_address']))


class MemoryQueryBackendTestCase(unittest.TestCase, QueryBackendTestCase):
    def _new_query_backend(self):
        return query.MemoryQueryBackend()


class LocalDistQueryBackendTestCase(MemoryQueryBackendTestCase):
    def _new_query_backend(self):
        return query.LocalFileQueryBackend()
