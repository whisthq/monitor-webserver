from .imports import *    

# Logging
class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True


syslog = SysLogHandler(address=(os.getenv("LOGGER_URL"), 44138))
syslog.addFilter(ContextFilter())

format = "%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] [MONITOR]: %(message)s"

formatter = logging.Formatter(format, datefmt="%b %d %H:%M:%S")
syslog.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(syslog)
logger.setLevel(logging.INFO)


def sendDebug(log, papertrail=True):
    """Logs debug messages

    Args:
        log (str): The message
        papertrail (bool, optional): Whether or not to send to papertrail. Defaults to True.
    """
    if papertrail:
        logger.debug(log)
    print(log)


def sendInfo(log, papertrail=True):
    """Logs info messages

    Args:
        log (str): The message
        papertrail (bool, optional): Whether or not to send to papertrail. Defaults to True.
    """
    if papertrail:
        logger.info(log)
    print(log)


def sendError(log, papertrail=True):
    """Logs errors

    Args:
        log (str): The message
        papertrail (bool, optional): Whether or not to send to papertrail. Defaults to True.
    """
    if papertrail:
        logger.error(log)
    print(log)

def sendCritical(log, papertrail=True):
    """Logs critical errors

    Args:
        log (str): The message
        papertrail (bool, optional): Whether or not to send to papertrail. Defaults to True.
    """
    if papertrail:
        logger.critical(log)
    print(log)

