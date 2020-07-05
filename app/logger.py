from .imports import *

# Logging
# class ContextFilter(logging.Filter):
#     hostname = socket.gethostname()

#     def filter(self, record):
#         record.hostname = ContextFilter.hostname
#         return True


# syslog = SysLogHandler(address=(os.getenv("LOGGER_URL"), 15317))
# syslog.addFilter(ContextFilter())

# format = "%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] [MONITOR]: %(message)s"

# formatter = logging.Formatter(format, datefmt="%b %d %H:%M:%S")
# syslog.setFormatter(formatter)

logger = logging.getLogger()
# logger.addHandler(syslog)
logger.setLevel(logging.INFO)


def sendDebug(log, upload_logs_to_cloud=True):
    """Logs debug messages

    Args:
        log (str): The message
        upload_logs_to_cloud (bool, optional): Whether or not to send to Datadog. Defaults to True.
    """
    # if upload_logs_to_cloud:
    #     logger.debug(log)
    print(log)


def sendInfo(log, upload_logs_to_cloud=True):
    """Logs info messages

    Args:
        log (str): The message
        upload_logs_to_cloud (bool, optional): Whether or not to send to Datadog. Defaults to True.
    # """
    # if upload_logs_to_cloud:
    #     logger.info(log)
    print(log)


def sendWarning(log, upload_logs_to_cloud=True):
    """Logs warning messages

    Args:
        log (str): The message
        upload_logs_to_cloud (bool, optional): Whether or not to send to Datadog. Defaults to True.
    """
    # if upload_logs_to_cloud:
    #     logger.warning(log)
    print(log)


def sendError(log, upload_logs_to_cloud=True):
    """Logs errors

    Args:
        log (str): The message
        upload_logs_to_cloud (bool, optional): Whether or not to send to Datadog. Defaults to True.
    """
    # if upload_logs_to_cloud:
    #     logger.error(log)
    print(log)


def sendCritical(log, upload_logs_to_cloud=True):
    """Logs critical errors

    Args:
        log (str): The message
        upload_logs_to_cloud (bool, optional): Whether or not to send to Datadog. Defaults to True.
    """
    # if upload_logs_to_cloud:
    #     logger.critical(log)
    print(log)
