import logging
from flask import current_app, abort, request
from functools import wraps

AUTH_ROLES = {
    'discovery': 'discovery',
    'lyftapi': 'lyftapi',
    'tom': 'tom',
}


def basic_authenticate(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        if not current_app.config.get("USE_AUTH"):
            return f(*args, **kwargs)

        if not getattr(f, 'basic_authenticate', True):
            return f(*args, **kwargs)

        auth = request.authorization

        if auth and auth.username and auth.password != '':
            password = current_app.config.get("{}_PASSWORD".format(auth.username.upper()))

            if auth.password == password:
                role = AUTH_ROLES[auth.username]
                logging.debug("Authenticated '{}' with role '{}' via basic auth".format(auth.username, role))
                current_app.auth_role = role
                return f(*args, **kwargs)

        return abort(401)
    return decorated
