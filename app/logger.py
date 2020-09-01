import sys
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
logger.setLevel(logging.WARNING)


def sendDebug(log):
    """Logs debug messages

    Args:
        N/A
    """
    print(
        "DEBUG: " + str(log), file=sys.stdout,
    )
    return None


def sendInfo(log):
    """Logs info messages

    Args:
        N/A
    # """
    print(
        "INFO: " + str(log), file=sys.stdout,
    )
    return None


def sendError(log):
    """Logs errors

    Args:
        N/A
    """
    print(
        "ERROR: " + str(log), file=sys.stderr,
    )
    return None
