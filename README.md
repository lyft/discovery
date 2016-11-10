#discovery

This service provides a REST interface for querying for the list of hosts that belong to a given service in microservice infrastructure.
Host information is written to and read from backend store (DynamoDB by default). This project relies on the following libraries:
* Flask (web-framework)
* Flask-Cache (for caching and reusing results for GET requests)
* Pynamodb (for reading/writing DynamoDB data)

##API
###GET /v1/registration/:service
Returns metadata for the given :service.

URL:
:service
  *(required, string)* Name of the service metadata is queried for.

Response:
```json
{
    "env": "...",
    "hosts": [
        {
            "ip_address": "...",
            "last_check_in": "...",
            "port": 9211,
            "revision": "...",
            "service": "...",
            "service_repo_name": "...",
            "tags": {
                "az": "...",
                "base_revision": "...",
                "canary": true,
                "instance_id": "...",
                "onebox_name": "...",
                "region": "..."
            }
        }
    ],
    "service": "..."
}
```

Describe all of the above.

###GET /v1/registration/repo/:service_repo_name
Returns the list of hosts for :service_repo_name (query based on secondary index, for example, DynamoDB GSI).
Format is the same as [above](#get-v1registrationservice)

###POST /v1/registration/:service
Used to register a host with a service.

Url:
  :service
    *(required, string)* Service for which operation is performed.

Request params:
The list of required parameters is as follows:
    ip
      *(required, string)* ip address of the host.
    port
      *(required, integer)* port on which the host expects connections.
    revision
      *(required, string)* SHA of the revision the service is currently running.
    tags
      *(required, object)* JSON in the following format

```json
  {
     "az": "us-east-1a",
     "region": "us-east-1",
     "instance_id": "i-934342",
     "canary": "true",
     "load_balancing_weight": "3"
  }
```

az
  *(required, string)* AWS availability zone that the host is running in. You
  can provide arbitrary but the same value for all hosts if zone aware stats/routing
  is not required.

region
    *(required, string)* AWS region that the host is running in.

instance_id
  *(required, string)* AWS instance_id of the host.

canary
  *(optional, boolean)* Set to true if host is a canary instance.

load_balancing_weight:
  *(optional, integer)* Used by Envoy for weighted routing. Values must be in a range of [1;100].

###DELETE /v1/registration/:service/:ip_address
Deletes the host for the given :service and :ip_address

###POST /v1/loadbalancing/:service/:ip_address
Used to update the weight of hosts for load balancing purposes.

Url:
:service
  *(required, string)* Service name for which weight is updated.
:ip_address
  *(optional, string)* IP address of the host for which weight is updated.
  If not given, *all* hosts for the given service will have their weights updated.

Request params:
load_balancing_weight
  *(required, integer)* Host weight, an integer between 1 and 100.

##Main Classes
- [app/routes/api.py](https://github.com/lyft/discovery/blob/master/app/routes/api.py)
 - defines the HTTP routes for service registration
- [app/resources/api.py](https://github.com/lyft/discovery/blob/master/app/resources/api.py)
 - the entry point for service registration GETs and POSTs
- [app/services/host.py](https://github.com/lyft/discovery/blob/master/app/services/host.py)
 - contains the business logic (e.g. caching, input validation, etc) for service registration GETS and POSTs
- [app/models/host.py](https://github.com/lyft/discovery/blob/master/app/models/host.py)
 - The pynamo model for service registration information for a host

##Unit Testing
*Note* currently it's not working on public repository without tweaking (there is an opened issue for this)
To run all unit tests, run `make test_unit`.
