from flask import Flask
from flask.ext import restful
from flask.ext.cache import Cache
from . import settings
from werkzeug.contrib.fixers import ProxyFix

app = Flask(__name__, static_folder='public')
app.config.from_object(settings)
app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=1)
api = restful.Api(app)
app.cache = Cache(app, config={'CACHE_TYPE': settings.CACHE_TYPE})


@app.route('/healthcheck')
def healthcheck():
    # The healthcheck returns status code 200
    return 'OK'

from . import routes  # noqa
