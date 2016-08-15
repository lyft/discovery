import logging
import socket
import datetime
import pytz

from flask import current_app as app
from flask import request

from app.stats import get_stats
from .. import settings
from ..models.host import Host


class HostService():
    '''Provides methods for querying for hosts'''

    def list(self, service):
        '''Returns a json list of hosts for that service.  Caches host lists per service with a TTL'''
        cached_hosts = app.cache.get(service)
        if cached_hosts:
            return cached_hosts

        cursor = Host.query(service)
        hosts = self._hosts_from_pynamo_cursor(cursor)
        app.cache.set(service, hosts, settings.CACHE_TTL)
        return hosts

    def list_by_service_repo_name(self, service_repo_name):
        '''Returns a json list of hosts for that service_repo_name.'''
        # Currently we don't cache calls that lookup via service_repo_name since the only
        # user is low rate and check.py. If we ever want caching on this call, we have to use
        # a separate cache from above or prepend a prefix since otherwise it will stomp.
        cursor = Host.service_repo_name_index.query(service_repo_name)
        hosts = self._hosts_from_pynamo_cursor(cursor)
        return hosts

    def update(self, service, ip_address, service_repo_name, port, revision, last_check_in, tags):
        '''Updates the service registration entry for one host. Returns True on success, False on failure'''

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
        host = Host.get(service, ip_address)
        host.tags[tag_name] = tag_value
        host.save()

    def set_tag_all(self, service, tag_name, tag_value):
        """Sets a tag on all hosts for the given service.

        It should be noted that the batch write is NOT ATOMIC. Batch writes are
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
        with Host.batch_write() as batch:
            for host in list(Host.query(service)):
                if host.tags.get(tag_name) != tag_value:
                    host.tags[tag_name] = tag_value
                    batch.save(host)

    def delete(self, service, ip_address):
        '''Attempts to delete the host.  Returns a boolean indicating success or failure'''
        if not service:
            logging.error("Delete: Missing required parameter - service")
            return False

        if not ip_address:
            logging.error("Delete: Missing required parameter - ip_address")
            return False

        if not self._is_valid_ip(ip_address):
            logging.error("Delete: Invalid ip address")
            return False

        statsd = get_stats('service.host')
        cursor = Host.query(service, ip_address__eq=ip_address)
        host = None
        try:
            host = cursor.next()
        except StopIteration:
            logging.error(
                "Delete called for nonexistent host: service=%s ip=%s" % (service, ip_address)
            )
            return False

        try:
            cursor.next()
            logging.error(
                "Returned more than 1 result for query %s %s.  Aborting the delete"
                % (service, ip_address)
            )
            return False
        except StopIteration:
            host.delete()
            statsd.incr("delete.%s" % service)
            return True

    def _sweep_host(self, host):
        '''
        Removes the host from the database. Used by the sweeper to remove expired hosts
        '''
        statsd = get_stats('service.host')
        host.delete()
        statsd.incr("sweep.%s" % host.service)

    def _is_expired(self, host):
        last_check_in = host.last_check_in
        now = datetime.datetime.now()

        if not last_check_in.tzinfo:
            last_check_in = pytz.utc.localize(last_check_in)
        if not now.tzinfo:
            now = pytz.utc.localize(now)
        # datetime.now(tz.tzutc()) and datetime.utcnow() do not return a tz-aware datetime
        # as a result, we use pytz to localize the timestamp to the UTC timezone
        time_elapsed = (now - last_check_in).total_seconds()
        if time_elapsed > settings.HOST_TTL:
            logging.info(
                "Expiring host %s for service %s because %d seconds have elapsed since last_checkin"
                % (host.tags['instance_id'], host.service, time_elapsed)
                )
            return True
        else:
            return False

    def _create_or_update_host(self, service, ip_address, service_repo_name, port, revision, last_check_in, tags):
        '''
        Create a new dynamo host entry or update an existing entry
        '''
        try:
            host = Host.get(service, ip_address)
            host.service_repo_name = service_repo_name
            host.port = port
            host.revision = revision
            host.last_check_in = last_check_in
            host.tags.update(tags)
        except Host.DoesNotExist:
            host = Host(
                service,
                ip_address=ip_address,
                service_repo_name=service_repo_name,
                port=port,
                revision=revision,
                last_check_in=last_check_in,
                tags=tags
            )
        host.save()

    def _hosts_from_pynamo_cursor(self, cursor):
        hosts = []
        for entry in cursor:
            if self._is_expired(entry):
                self._sweep_host(entry)
            else:
                hosts.append(self._pynamo_host_to_dict(entry))
        return hosts

    def _is_valid_ip(self, ip_str):
        '''
        Returns whether the given string is a valid ip address
        '''
        try:
            socket.inet_pton(socket.AF_INET, ip_str)
            return ip_str.count('.') == 3
        except socket.error:
            pass
        return False

    def _pynamo_host_to_dict(self, entry):
        host = {}
        host['service'] = entry.service
        host['ip_address'] = entry.ip_address
        host['service_repo_name'] = entry.service_repo_name
        host['port'] = entry.port
        host['revision'] = entry.revision
        host['last_check_in'] = str(entry.last_check_in)
        host['tags'] = entry.tags
        return host
