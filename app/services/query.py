import abc
import logging
import os
import pickle
import tempfile

from ..stats import get_stats
from ..models.host import Host


class QueryBackend(object):
    __metaclass__ = abc.ABCMeta
    """A storage backend that can store and retrieve host data.

    This is modeled off of the dynamodb python API, but made more
    general so users not on Amazon can use discovery.
    """

    @abc.abstractmethod
    def query(self, service):
        """Returns a generator of host dicts for the given service.

        Note that this will NOT deal with how timing out entries -- that is
        a concern of the caller.

        :param service: service of the hosts to retrieve

        :type service: str

        :returns: hosts associated with this service
        :rtype: list(dict)
        """

        pass

    @abc.abstractmethod
    def query_secondary_index(self, service_repo_name):
        """For backends that support secondary indices, allows more efficient querying.

        :param service_repo_name: service_repo_name to retrieve associated hosts for

        :type service_repo_name: str

        :returns: hosts associated with this service_repo_name
        :rtype: list(dict)
        """

        pass

    @abc.abstractmethod
    def get(self, service, endpoint):
        """Fetches the single host associated with the given service and ip_address

        :param service: the service of the host to get
        :param endpoint: the ip_address of the host to get

        :type service: str
        :type endpoint: str

        :returns: a single host if one exists, None otherwise
        :rtype: dict
        """

        pass

    @abc.abstractmethod
    def put(self, host):
        """Attempts to store the given host

        :param host: host entry to store

        :type host: dict

        :returns: True if put successful, False otherwise
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def delete(self, service, ip_address):
        """Deletes the given host for the given service/ip_address

        :param service: the service of the host to delete
        :param ip_address: the ip_address of the host to delete

        :type service: str
        :type ip_address: str

        :returns: True if delete successful, False otherwise
        :rtype: bool
        """

        pass

    def batch_put(self, hosts):
        '''Batch write interface for backends which support more efficient batch storing methods.

        Note: even for backends that support this, do NOT assume that it is atomic! That depends on
        the backend, but is not a semantic enforced by this API. If this fails, it is possible that
        some values have been partially written. This needs to be handled by the caller.

        :param hosts: list of host dicts to write

        :type hosts: list(dict)

        :returns: True if all writes successful, False if 1 or more fail
        :rtype: bool
        '''
        return all(map(self.store, hosts))


# TODO need to factor out the statsd dep
class MemoryQueryBackend(QueryBackend):
    def __init__(self):
        self.data = {}

    def _list_all(self):
        """A generator over every host that has been stored."""

        for service in self.data.keys():
            for r in self.query(service):
                yield r

    def query(self, service):
        ip_map = self.data.get(service)
        if ip_map is None:
            return

        for ip_address, host_dict in ip_map.items():
            _host = host_dict.copy()
            _host['service'] = service
            _host['ip_address'] = ip_address
            yield _host

    # TODO this can certainly be made faster, but I don't know if that's
    # really necessary...
    def query_secondary_index(self, service_repo_name):
        for host in self._list_all():
            if host['service_repo_name'] == service_repo_name:
                yield host

    def get(self, service, endpoint):
        ip_map = self.data.get(service)
        if ip_map is None:
            return None

        host_dict = ip_map.get(endpoint)
        if host_dict is None:
            return None

        host = host_dict.copy()
        host['service'] = service
        host['ip_address'] = endpoint
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
        return True

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
        """Saves the data information to local file."""

        pickle.dump(self.backend.data, open(self.file, 'w'))

    def query(self, service):
        return self.backend.query(service)

    def query_secondary_index(self, service_repo_name):
        return self.backend.query_secondary_index(service_repo_name)

    def get(self, service, endpoint):
        return self.backend.get(service, endpoint)

    def put(self, host):
        try:
            return self.backend.put(host)
        finally:
            self._save()

    def delete(self, service, ip_address):
        try:
            return self.backend.delete(service, ip_address)
        finally:
            self._save()


class DynamoQueryBackend(QueryBackend):
    def query(self, service):
        return self._read_cursor(Host.query(service))

    def query_secondary_index(self, service_repo_name):
        return self._read_cursor(Host.service_repo_name_index.query(service_repo_name))

    def get(self, service, endpoint):
        try:
            host = Host.get(service, endpoint)
            if host is None:
                return None
            return self._pynamo_host_to_dict(host)
        except Host.DoesNotExist:
            return None

    def put(self, host):
        self._dict_to_pynamo_host(host).save()

    def batch_put(self, hosts):
        """
        Note! Batched writes in pynamo are NOT ATOMIC. Batch writes are
        done in groups of 25 with pynamo handling retries for partial failures
        in a batch. It's possible that retries can be exhausted and we could
        end up in a state where some weights were written and others weren't,
        so external users should always ensure that weights were all
        propagated and explicitly retry if not.

        It's also possible that we're overriding newer data from hosts since
        we're putting the whole host object rather than just updating an
        individual field. This should be OK in practice as the time frame is
        short and the next host update will return things to normal.
        """

        # TODO need to look at the exceptions dynamo can throw here, catch, return False
        with Host.batch_write() as batch:
            for host in hosts:
                batch.save(self._dict_to_pynamo_host(host))
        return True

    def delete(self, service, ip_address):
        """
        Technically we should not have several entries for the given service and ip address.
        But there is no guarantee that it must be the case. Here we verify that it's strictly
        one registered service/ip.
        """

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
            self._dict_to_pynamo_host(hosts[0]).delete()
            statsd.incr("delete.%s" % service)
            return True

    def _read_cursor(self, cursor):
        """Converts a pynamo cursor into a generator.

        :param cursor: pynamo cursor

        :type cursor: TODO dig it up, some pynamo nonsense

        :returns: generator based on the cursor
        :retype: generator(dict)
        """

        for host in cursor:
            yield self._pynamo_host_to_dict(host)

    def _pynamo_host_to_dict(self, host):
        """Converts a pynamo host into a dict.

        :param host: pynamo host

        :type host: Host

        :returns: dictionary with host info
        :rtype: dict
        """

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
        """Converts a dict to a pynamo host.

        Note that if any keys are missing, there will be an error.

        :param host: dict with host info

        :type host: dict

        :returns: pynamo Host
        :rtype: Host
        """

        return Host(service=host['service'],
                    endpoint=host['endpoint'],
                    ip_address=host['ip_address'],
                    service_repo_name=host['service_repo_name'],
                    port=host['port'],
                    revision=host['revision'],
                    last_check_in=host['last_check_in'],
                    tags=host['tags'])
