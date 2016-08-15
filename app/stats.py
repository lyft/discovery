import os

import statsd


def get_stats(prefix):
    host = os.environ.get('STATSD_HOST', 'localhost')
    port = int(os.environ.get('STATSD_PORT', 8125))
    stats = statsd.StatsClient(host, port, prefix=prefix)
    return stats
