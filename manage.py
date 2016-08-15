# flake8: noqa
#!/usr/bin/env python

import gevent.monkey

gevent.monkey.patch_all()

from flask.ext.script import Manager

from app import app
from app.scripts.hello import Hello

manager = Manager(app)

manager.add_command("hello", Hello)

if __name__ == "__main__":
    manager.run()
