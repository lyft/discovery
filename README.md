#discovery

This service provides a REST interface for querying for the list of hosts that belong to a given service in microservice infrastructure.
Host information is written to and read from Dynamo. This project relies on the following libraries:
* Flask (web-framework)
* Flask-Cache (for caching and reusing results for GET requests)
* Pynamodb (for reading/writing DynamoDB data)

##API
###GET /v1/registration/:service
- Returns the list of hosts for :service

###GET /v1/registration/repo/:service_repo_name
- Returns the list of hosts for :service_repo_name (queries a Dynamodb GSI for this info)

###POST /v1/registration/:service
- Used to register a host with a service. The list of required parameters is as follows:
 - ip (the ip address of the host)
 - port (the port on which the host expects connections)
 - revision (the sha of the github revision the service is currently running)
 - tags (a JSON dictionary with the following fields)
   - az (Required: the AWS availability zone that the host is running in)
    - region (Required: the AWS region that the host is running in)
    - instance_id (Required: the AWS instance_id of the host)
    - canary (Optional: boolean string set to  "true" if the host is a canary)
    - load_balancing_weight (Optional: may be used for load balancing)

###DELETE /v1/registration/:service/:ip_address
- Deletes the host for the given :service and :ip_address

###POST /v1/loadbalancing/:service/:ip_address
- Used to update the weight of hosts for load balancing purposes.
- `:ip_address` is optional. If not given, _all_ hosts for the given service will have their weights updated.
- The list of required parameters is as follows:
 - load_balancing_weight (an integer between 1 and 100)

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
To run all unit tests, run `make test_unit`.
