import logging

__version__ = "0.1.0a0"

_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger(__name__).addHandler(_handler)
logging.getLogger(__name__).setLevel(logging.DEBUG)
