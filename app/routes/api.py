from .. import api
from ..resources.api import Registration, RepoRegistration, LoadBalancing

# Add your resources here
api.add_resource(Registration,
                 '/v1/registration/<service>',
                 '/v1/registration/<service>/<ip_address>')
api.add_resource(RepoRegistration, '/v1/registration/repo/<service_repo_name>')
api.add_resource(LoadBalancing,
                 '/v1/loadbalancing/<service>',
                 '/v1/loadbalancing/<service>/<ip_address>')
