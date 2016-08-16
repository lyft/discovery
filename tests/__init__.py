import logging

logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('pynamodb').setLevel(logging.WARNING)
