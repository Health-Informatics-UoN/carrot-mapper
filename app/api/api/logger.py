import logging

logger = logging.getLogger("api_test_logger")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%d/%m/%Y %H:%M:%S"
    )
)
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)  # Set to logging.DEBUG to show the debug output
