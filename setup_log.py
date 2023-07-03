import logging


def setup_logging():
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)
  info_handler = logging.FileHandler("logger_info.log")
  info_handler.setLevel(logging.INFO)
  log_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s")
  info_handler.setFormatter(log_formatter)
  logger.addHandler(info_handler)
  debug_logger = logging.getLogger("debug")
  debug_logger.setLevel(logging.DEBUG)
  debug_handler = logging.FileHandler("logger_debug.log")
  debug_handler.setLevel(logging.DEBUG)
  debug_handler.setFormatter(log_formatter)
  debug_logger.addHandler(debug_handler)
  return logger, debug_logger
