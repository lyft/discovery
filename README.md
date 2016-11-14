# Discovery

This service provides a REST interface for querying for the list of hosts that belong to a given service in microservice infrastructure.
Host information is written to and read from backend store (DynamoDB by default). This project relies on the following libraries:
* Flask (web-framework)
* Flask-Cache (for caching and reusing results for GET requests)
* Pynamodb (for reading/writing DynamoDB data)

## API
### GET /v1/registration/:service
Returns metadata for the given `:service`.

* service
  * *(required, string)* name of the service metadata is queried for.

On successful response, response body will be in the following JSON format:
```json
{
    "env": "...",
    "hosts": [],
    "service": "..."
}
```
* env
  * *(required, string)* environment discovery service runs in, e.g., development or production.
* hosts
  * *(required, object)* list of non expired hosts (hosts that last checked in to discovery service in the last HOST_TTL period).
  Each host is in the following JSON format:

    ```json
    {
        "ip_address": "...",
        "last_check_in": "...",
        "port": 9211,
        "revision": "...",
        "service": "...",
        "service_repo_name": "...",
        "tags": {}
    }
    ```
  * ip_address
    * *(required, string)* ip address of the host.
  * last_check_in
    * *(required, string)* heartbeat timestamp converted to string, last time host registered with discovery service.
  * port
    * *(required, integer)* port on which the host expects connections, Envoy will connect to this port.
  * revision
    * *(required, string)* service SHA running on the host.
  * service
    * *(required, string)* service name.
  * service_repo_name
    * *(required, string)* service repo, used for selecting hosts based on the service_repo (can be empty if not set).
  * tags
    * *(required, object)* see tags [here](#tags-json).
* service
  * *(required, string)* service name.

### GET /v1/registration/repo/:service_repo_name
Returns list of non expired hosts for `:service_repo_name` (query based on secondary index, for example, DynamoDB GSI).
Format is the same as [query based on service](#get-v1registrationservice).

### POST /v1/registration/:service
Registers a host with a service. Response body does not contain any data.

* service
  * *(required, string)* Service for which operation is performed.

Request params:
* ip
  * *(required, string)* ip address of the host.
* service_repo_name
  * *(optional, string)* service repository name, can be used for quick search.
* port
  * *(required, integer)* port on which the host expects connections, Envoy will connect to this port.
* revision
  * *(required, string)* SHA of the revision the service is currently running.
* tags
  * *(required, object)* JSON in the following [format](#tags-json).

### DELETE /v1/registration/:service/:ip_address
Deletes the host for the given `service` with `ip_address`.
Returns response code 400 if no `service`/`ip_address` entity exists.

* service
  * *(required, string)* name of the service metadata is queried for.
* ip
  * *(required, string)* ip address of the host.

### POST /v1/loadbalancing/:service/:ip_address
Updates the weight of hosts for load balancing purposes.

* service
  * *(required, string)* Service name for which weight is updated.
* ip_address
  * *(optional, string)* IP address of the host for which weight is updated.
  If not given, *all* hosts for the given service will have their weights updated.

Request params:
* load_balancing_weight
  * *(required, integer)* Host weight, an integer between 1 and 100.

#### Tags JSON
```json
  {
     "az": "...",
     "region": "...",
     "instance_id": "...",
     "canary": true,
     "load_balancing_weight": 3
  }
```

* az
  * *(required, string)* AWS availability zone that the host is running in. You
  can provide arbitrary but the same value for all hosts if zone aware stats/routing
  is not required. If you use non AWS backend storage currently you have to provide `az`
  anyway, you can use some fixed predefined value for all hosts.
* region
  * *(required, string)* AWS region that the host is running in.
* instance_id
  * *(required, string)* AWS instance_id of the host.
* canary
  * *(optional, boolean)* Set to true if host is a canary instance, used by Envoy.
* load_balancing_weight:
  * *(optional, integer)* Load balancing weight is used by Envoy for weighted routing.
  Values must be an integer between 1 and 100.

## Main Classes
- [app/routes/api.py](https://github.com/lyft/discovery/blob/master/app/routes/api.py)
 - defines the HTTP routes for service registration
- [app/resources/api.py](https://github.com/lyft/discovery/blob/master/app/resources/api.py)
 - the entry point for service registration GETs and POSTs
- [app/services/host.py](https://github.com/lyft/discovery/blob/master/app/services/host.py)
 - contains the business logic (e.g. caching, input validation, etc) for service registration GETS and POSTs
- [app/models/host.py](https://github.com/lyft/discovery/blob/master/app/models/host.py)
 - The pynamo model for service registration information for a host

## Unit Testing
*Note* currently it's not working on public repository without tweaking (there is an opened issue for this)
To run all unit tests, run `make test_unit`.
