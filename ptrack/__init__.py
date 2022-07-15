import logging

logging.root.setLevel(logging.DEBUG)
logging.disable(logging.NOTSET)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s %(levelname)-8s] %(name)-12s: %(message)s'))
logger.addHandler(handler)

