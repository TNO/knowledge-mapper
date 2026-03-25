import logging


def get_example_logger(name: str) -> logging.Logger:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(f"%(asctime)s [%(levelname)s] [{name}-example] %(message)s")
    )
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
