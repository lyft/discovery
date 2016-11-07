import json
import logging
from datetime import datetime

from flask import request
from flask.ext.restful import Resource

from ..stats import get_stats
from .. import settings
from ..services import host

logger = logging.getLogger('resources.api')
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)s: %(levelname)s %(message)s')


class HostSerializer(object):

    @staticmethod
    def serialize(hosts):
        '''Makes host dictionary serializable

        :param hosts: list of hosts, each host is defined by dict host info
        :type hosts: dict

        :returns: list of host info dictionaries
        :rtype: list of dict
        '''

        for _host in hosts:
            _host['last_check_in'] = str(_host['last_check_in'])

        return hosts


class Registration(Resource):

    def get(self, service):
        '''Return all the hosts registered for this service'''
        host_service = host.HostService()
        hosts = host_service.list(service)
        response = {
            'service': service,
            'env': settings.APPLICATION_ENV,
            'hosts': HostSerializer.serialize(hosts)
        }
        return response, 200

    def post(self, service):
        '''Update or add a service registration given the host information in this request'''
        ip_address = self._get_param('ip', None)
        if not ip_address and self._get_param('auto_ip', None):
            # Discovery ELB is the single proxy, take last ip in route
            forwarded_for = request.remote_addr
            parts = forwarded_for.split('.')
            # 192.168.0.0/16
            valid = (len(parts) == 4 and
                     int(parts[0]) == 192 and
                     int(parts[1]) == 168 and
                     0 <= int(parts[2]) <= 255 and
                     0 <= int(parts[3]) <= 255)
            if valid:
                ip_address = forwarded_for
                logger.info('msg="auto_ip success" service={}, auto_ip={}'
                            .format(service, ip_address))
            else:
                logger.warn('msg="auto_ip invalid" service={} auto_ip={}'
                            .format(service, ip_address))
        service_repo_name = self._get_param('service_repo_name', '')
        port = int(self._get_param('port', -1))
        revision = self._get_param('revision', None)
        last_check_in = datetime.utcnow()
        tags = self._get_param('tags', '{}')

        try:
            tags = json.loads(tags)
        except ValueError as ex:
            logger.exception("Failed to parse tags json: {}. Exception: {}".format(tags, ex))
            return {"error": "Invalid json supplied in tags"}, 400

        host_service = host.HostService()
        success = host_service.update(service, ip_address, service_repo_name,
                                      port, revision, last_check_in, tags)

        statsd = get_stats("registration")
        if success:
            response_code = 200
            statsd.incr("%s.success" % service)
        else:
            response_code = 400
            statsd.incr("%s.failure" % service)
        return {}, response_code

    def delete(self, service, ip_address):
        '''Delete a host from dynamo'''
        host_service = host.HostService()
        success = host_service.delete(service, ip_address)
        response_code = 200 if success else 400
        return {}, response_code

    def _get_param(self, param, default=None):
        '''Return the request parameter.  Returns default if the param was not found'''
        return request.form[param] if param in request.form else default


class RepoRegistration(Resource):

    def get(self, service_repo_name):
        '''Return all the hosts that belong to the service_repo_name'''
        host_service = host.HostService()
        hosts = host_service.list_by_service_repo_name(service_repo_name)
        response = {
            'service_repo_name': service_repo_name,
            'env': settings.APPLICATION_ENV,
            'hosts': HostSerializer.serialize(hosts)
        }
        return response, 200


class LoadBalancing(Resource):

    def post(self, service, ip_address=None):
        weight = request.form.get('load_balancing_weight')
        if not weight:
            return {"error": "Required parameter 'weight' is missing."}, 400

        try:
            weight = int(weight)
        except ValueError:
            weight = None

        if not weight or not 1 <= weight <= 100:
            return {"error": ("Invalid load_balancing_weight. Supply an "
                              "integer between 1 and 100.")}, 400

        host_service = host.HostService()

        if ip_address:
            if not host_service.set_tag(service, ip_address, 'load_balancing_weight', weight):
                return {"error": "Host not found"}, 404
        else:
            host_service.set_tag_all(service, 'load_balancing_weight', weight)

        return "", 204
