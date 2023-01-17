import logging

formatter = logging.Formatter(fmt='%(asctime)s : %(name)s :: %(levelname)-8s :: %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)

logger.addHandler(console_handler)