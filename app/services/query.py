import abc
import logging
import os
import pickle
import tempfile

from ..stats import get_stats
from ..models.host import Host


class QueryBackend(object):
    __metaclass__ = abc.ABCMeta
    '''A storage backend that can store and retrieve host data.

    This is modeled off of the dynamodb python API, but made more
    general so users not on Amazon can use discovery.
    '''
    @abc.abstractmethod
    def query(self, service):
        '''Returns a generator of host dicts for the given service.

        Note that this will NOT deal with how timing out entries -- that is
        a concern of the caller.
        '''
        pass

    @abc.abstractmethod
    def query_secondary_index(self, service_repo_name):
        '''For backends that support secondary indices, allows more efficient querying'''
        pass

    @abc.abstractmethod
    def get(self, service, ip_address):
        '''Returns a single value for the given service/ip_address, if one exists, None otherwise'''
        pass

    @abc.abstractmethod
    def put(self, host):
        '''Attempts to store the given host'''
        pass

    @abc.abstractmethod
    def delete(self, service, ip_address):
        '''Deletes the given host for the given service/ip_address, returning True if successful'''
        pass

    def batch_put(self, hosts):
        '''Batch write interface for backends which support more efficient batch storing methods'''
        for host in hosts:
            self.store(host)


# TODO need to factor out the statsd dep
class MemoryQueryBackend(QueryBackend):
    def __init__(self):
        self.data = {}

    def _list_all(self):
        for service in self.data.keys():
            for r in self.query(service):
                yield r

    def query(self, service):
        ip_map = self.data.get(service)
        if ip_map is None:
            return

        for ip_address, host_dict in ip_map.iteritems():
            _host = host_dict.copy()
            _host['service'] = service
            _host['ip_address'] = ip_address
            yield _host

    # TODO this can certainly be made faster, but I don't know if that's
    #      really necessary...
    def query_secondary_index(self, service_repo_name):
        for host in self._list_all():
            if host['service_repo_name'] == service_repo_name:
                yield host

    def get(self, service, ip_address):
        ip_map = self.data.get(service)
        if ip_map is None:
            return None

        host_dict = ip_map.get(ip_address)
        if host_dict is None:
            return None

        host = host_dict.copy()
        host['service'] = service
        host['ip_address'] = ip_address
        return host

    def put(self, host):
        service = host['service']
        ip_address = host['ip_address']

        ip_map = self.data.get(service)
        if ip_map is None:
            ip_map = {}
            self.data[service] = ip_map

        host_dict = host.copy()
        del host_dict['service']
        del host_dict['ip_address']

        ip_map[ip_address] = host_dict

    def delete(self, service, ip_address):
        ip_map = self.data.get(service)
        if ip_map is None:
            return False

        host_dict = ip_map.get(ip_address)
        if host_dict is None:
            return False

        del ip_map[ip_address]
        if len(ip_map) == 0:
            del self.data[service]
        return True


class LocalFileQueryBackend(QueryBackend):
    def __init__(self, file=tempfile.TemporaryFile().name):
        self.backend = MemoryQueryBackend()
        self.file = file
        if os.path.isfile(self.file) and os.stat(self.file).st_size > 0:
            self.backend.data = pickle.load(open(self.file))

    def _save(self):
        pickle.dump(self.backend.data, open(self.file, 'w'))

    def query(self, service):
        return self.backend.query(service)

    def query_secondary_index(self, service_repo_name):
        return self.backend.query_secondary_index(service_repo_name)

    def get(self, service, ip_address):
        return self.backend.get(service, ip_address)

    def put(self, host):
        self.backend.put(host)
        self._save()

    def delete(self, service, ip_address):
        self.backend.delete(service, ip_address)
        self._save()


class DynamoQueryBackend(QueryBackend):
    def query(self, service):
        return self._read_cursor(Host.query(service))

    def query_secondary_index(self, service_repo_name):
        return self._read_cursor(Host.service_repo_name_index.query(service_repo_name))

    def get(self, service, ip_address):
        try:
            host = Host.get(service, ip_address)
            if host is None:
                return None
            return self._pynamo_host_to_dict(host)
        except Host.DoesNotExist:
            return None

    def put(self, host):
        self._dict_to_pynamo_host(host).save()

    def batch_put(self, hosts):
        with Host.batch_write() as batch:
            for host in hosts:
                batch.save(self._dict_to_pynamo_host(host))

    # TODO is all of this pomp and circumstance really necessary to properly delete?
    #      need to better understand dynamodb
    def delete(self, service, ip_address):
        statsd = get_stats('service.host')
        hosts = list(self._read_cursor(Host.query(service, ip_address__eq=ip_address)))
        if len(hosts) == 0:
            logging.error(
                "Delete called for nonexistent host: service=%s ip=%s" % (service, ip_address)
            )
            return False
        elif len(hosts) > 1:
            logging.error(
                "Returned more than 1 result for query %s %s.  Aborting the delete"
                % (service, ip_address)
            )
            return False
        else:
            hosts[0].delete()
            statsd.incr("delete.%s" % service)
            return True

    def _read_cursor(self, cursor):
        for host in cursor:
            yield self._pynamo_host_to_dict(host)

    def _pynamo_host_to_dict(self, host):
        _host = {}
        _host['service'] = host.service
        _host['ip_address'] = host.ip_address
        _host['service_repo_name'] = host.service_repo_name
        _host['port'] = host.port
        _host['revision'] = host.revision
        _host['last_check_in'] = host.last_check_in
        _host['tags'] = host.tags
        return _host

    def _dict_to_pynamo_host(self, host):
        return Host(service=host['service'],
                    ip_address=host['ip_address'],
                    service_repo_name=host['service_repo_name'],
                    port=host['port'],
                    revision=host['revision'],
                    last_check_in=host['last_check_in'],
                    tags=host['tags'])
