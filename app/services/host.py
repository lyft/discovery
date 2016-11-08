import datetime
import logging
import pytz
import query
import socket

from flask import current_app as app
from flask import request

from ..stats import get_stats
from .. import settings


class HostService():
    '''Provides methods for querying for hosts'''

    def __init__(self, query_backend=query.DynamoQueryBackend()):
        '''
        Initialize HostService against a given query backend.

        :param query_backend: provides access to a storage engine for the hosts.
        :type query_backend: query.QueryBackend
        '''
        self.query_backend = query_backend

    def _sweep_expired_hosts(self, hosts):
        '''Filters out any hosts which have expired.

        :param hosts: a list of host dictionaries to check for expiration
        :type hosts: list(dict)

        :returns: filtered list of host dictionaries
        :rtype: list(dict)
        '''
        _hosts = []
        for host in hosts:
            if self._is_expired(host):
                statsd = get_stats('service.host')
                self.query_backend.delete(host['service'], host['ip_address'])
                statsd.incr("sweep.%s" % host['service'])
            else:
                _hosts.append(host)
        return _hosts

    def list(self, service):
        '''Returns a json list of hosts for that service.

        Caches host lists per service with a TTL.

        :param service: name of a service

        :type service: str

        :returns: all of the hosts associated with the given service
        :rtype: list(dict)
        '''
        cached_hosts = app.cache.get(service)
        if cached_hosts:
            return cached_hosts

        hosts = self._sweep_expired_hosts(self.query_backend.query(service))
        app.cache.set(service, hosts, settings.get('CACHE_TTL'))
        return hosts

    def list_by_service_repo_name(self, service_repo_name):
        '''Returns a json list of hosts for that service_repo_name.

        Note! Currently we don't cache calls that lookup via service_repo_name since the only
        use is low rate and check.py. If we ever want caching on this call, we have to use
        a separate cache from above or prepend a prefix since otherwise it will stomp.

        :param service_repo_name: service_repo_name to find entries associated with

        :type service_repo_name: str

        :returns: all of the hosts associated with the given service_repo_name
        :rtype: list(dict)
        '''
        return self._sweep_expired_hosts(self.query_backend.query_secondary_index(service_repo_name))

    def update(self, service, ip_address, service_repo_name, port, revision, last_check_in, tags):
        '''Updates the service registration entry for one host.

        :param service: the service to update
        :param ip_address: the ip address of the host
        :param service_repo_name: the repo of the service
        :param port: the port of the host
        :param revision: the revision of the host
        :param last_check_in: the last check in
        :param tags: matadata associated with the host. az, instance_id, and region are required

        :type service: str
        :type ip_address: str
        :type service_repo_name: str
        :type port: int
        :type revision: str
        :type last_check_in: datetime
        :type tags: dict

        :returns: True on success, False on failure
        :rtype: bool
        '''

        if not service:
            logging.error("Update: Missing required parameter - service")
            return False
        if not ip_address:
            logging.error(
                "Update: Missing required parameter - ip_address. url=%s params=%s" % (
                    request.url, request.form
                )
            )
            return False
        if not port:
            logging.error("Update: Missing required parameter - port")
            return False
        if not revision:
            logging.error("Update: Missing required parameter - revision")
            return False
        if not last_check_in:
            logging.error("Update: Missing required parameter - last_check_in")
            return False

        if(type(last_check_in).__name__ != 'datetime'):
            return False

        # validate that port is a positive number
        try:
            port = int(port)
        except ValueError:
            logging.error("Update: Invalid port")
            return False
        if port <= 0:
            logging.error("Update: Invalid port")
            return False

        if not self._is_valid_ip(ip_address):
            logging.error("Update: Invalid ip address")
            return False

        # TODO eventually we should be able to have this be pluggable -- non-amazon backends
        #      won't care
        if 'az' not in tags:
            logging.error("Update: Missing required tag - az")
            return False

        if 'instance_id' not in tags:
            logging.error("Update: Missing required tag - instance_id")
            return False

        if 'region' not in tags:
            logging.error("Update: Missing required tag - region")
            return False

        self._create_or_update_host(service, ip_address, service_repo_name, port, revision, last_check_in, tags)
        return True

    def set_tag(self, service, ip_address, tag_name, tag_value):
        '''Set a tag on the associated service/ip_address entry.

        :param service: the service to update
        :param ip_address: the ip address of the host
        :param tag_name: tag to update
        :param tag_value: value to update for given tag_name

        :type service: str
        :type ip_address: str
        :type tag_name: str
        :type tag_value: str

        :returns: True if update successful, False otherwise
        :rtype: bool
        '''
        # TODO note that we never sweep when we do a get... is that an error?
        host = self.query_backend.get(service, ip_address)
        if host is None:
            return False
        host['tags'][tag_name] = tag_value
        self.query_backend.put(host)
        return True

    def set_tag_all(self, service, tag_name, tag_value):
        '''Sets a tag on all hosts for the given service.

        It should be noted that the batch write is NOT guaranteed to be atomic.
        It depends on the underlying store QueryBackend. pynamo, for example,
        does not provide atomic batch writes.

        :param service: the service to update
        :param tag_name: tag to update
        :param tag_value: value to update for given tag_name

        :type service: str
        :type tag_name: str
        :type tag_value: str

        :returns: True if update successful, False otherwise. Note that False
                  indicates that 1 or more writes failed, and it is possible for
                  the tags to have been partially written to some entries
        :rtype: bool
        '''
        to_put = []
        for host in self.query_backend.query(service):
            if host['tags'].get(tag_name) != tag_value:
                host['tags'][tag_name] = tag_value
                to_put.append(host)
        return self.query_backend.batch_put(to_put)

    def delete(self, service, ip_address):
        '''Attempts to delete the host with the given service and ip_address.

        :param service: the service of the host to delete
        :param ip_address: the ip_address of the host to delete

        :type service: str
        :type ip_address: str

        :returns: True if delete successful, False otherwise
        :rtype: bool
        '''
        if not service:
            logging.error("Delete: Missing required parameter - service")
            return False

        if not ip_address:
            logging.error("Delete: Missing required parameter - ip_address")
            return False

        if not self._is_valid_ip(ip_address):
            logging.error("Delete: Invalid ip address")
            return False

        return self.query_backend.delete(service, ip_address)

    def _is_expired(self, host):
        '''Check if the given host is considered to be expired.

        Expiration is based on the value of HOST_TTL.

        :param host: the host dictionary with check in info

        :type: list(dict)

        :returns: True if host entry expired, False otherwise
        :rtype: bool
        '''
        last_check_in = host['last_check_in']
        now = datetime.datetime.now()

        if not last_check_in.tzinfo:
            last_check_in = pytz.utc.localize(last_check_in)
        if not now.tzinfo:
            now = pytz.utc.localize(now)
        # datetime.now(tz.tzutc()) and datetime.utcnow() do not return a tz-aware datetime
        # as a result, we use pytz to localize the timestamp to the UTC timezone
        time_elapsed = (now - last_check_in).total_seconds()
        if time_elapsed > settings.get('HOST_TTL'):
            logging.info(
                "Expiring host %s for service %s because %d seconds have elapsed since last_checkin"
                % (host['tags']['instance_id'], host['service'], time_elapsed)
                )
            return True
        else:
            return False

    def _create_or_update_host(self, service, ip_address, service_repo_name, port, revision, last_check_in, tags):
        '''
        Create a new host entry or update an existing entry.

        :param service: the service name of the host
        :param ip_address: the ip address of the host
        :param service_repo_name: the repo of the service
        :param port: the port of the host
        :param revision: the revision of the host
        :param last_check_in: the last check in
        :param tags: matadata associated with the host. az, instance_id, and region are required

        :type service: str
        :type ip_address: str
        :type service_repo_name: str
        :type port: int
        :type revision: str
        :type last_check_in: datetime
        :type tags: dict

        :returns: True on success, False on failure
        :rtype: bool
        '''
        host = self.query_backend.get(service, ip_address)
        if host is None:
            host = {
                'service': service,
                'ip_address': ip_address,
                'service_repo_name': service_repo_name,
                'port': port,
                'revision': revision,
                'last_check_in': last_check_in,
                'tags': tags
            }
        else:
            host['service_repo_name'] = service_repo_name
            host['port'] = port
            host['revision'] = revision
            host['last_check_in'] = last_check_in
            host['tags'].update(tags)
        return self.query_backend.put(host)

    def _is_valid_ip(self, ip):
        '''
        Returns whether the given string is a valid ip address.

        :param ip: ip address to validate
        :type ip: str

        :returns: True if valid, False otherwise
        :rtype: bool
        '''
        try:
            socket.inet_pton(socket.AF_INET, ip)
            return ip.count('.') == 3
        except socket.error:
            pass
        return False
