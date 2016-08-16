from discovery.app.models.host import Host


def setup():
    clear()


def teardown():
    clear()


def clear():
    for item in Host.scan():
        item.delete()
