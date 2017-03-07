'''Provides functions to quickly configure the logging system with
specific desired defaults. Does basic configuration for the logging
system by creating a logging.handlers.RotatingFileHandler and
StreamHandler with a default Formatter and adding it to the root
logger. Arguments fed to configure_file_and_console are forwarded to
RotatingFileHandler. Also provides functions that quickly configures
just a RotatingFileHandler and a StreamHandler with a formatter.
'''
import logging
from logging.handlers import RotatingFileHandler

LOGGER = logging.getLogger()
DEFAULT_FORMATTER \
    = logging.Formatter('%(asctime)s.%(msecs)03d %(module)-15s %(levelname)s - ''%(message)s',
                        datefmt='%Y-%m-%dT%H:%M:%S')
MAX_BYTES = int(1e8)  # Max 100M for logs
BACKUP_COUNT = 5


def configure_file_and_console(formatter=DEFAULT_FORMATTER,
                               level='INFO',
                               log_path='/tmp/%s.log' % __name__,
                               module_name=None,
                               *args, **kwargs):
    '''Configure a rotating file handler and stdout stream handler with
    the given arguments. This will remove any existing handlers on the
    root logger if the root logger is used. If this is not the desired
    functionality, see `quick_rot_file` and `quick_stdout`.
    '''
    if module_name:
        global LOGGER
        LOGGER = logging.getLogger(module_name)
    LOGGER.level = logging.getLevelName(level)
    console_level = kwargs.pop('console_level', LOGGER.level)
    file_level = kwargs.pop('file_level', LOGGER.level)
    quick_rot_file(log_path, file_level=file_level, formatter=formatter, *args, **kwargs)
    quick_stdout(formatter=formatter, console_level=console_level, *args, **kwargs)
    return LOGGER


def quick_rot_file(*args, **kwargs):
    '''Add a rotating file handler to the logger with the given arguments
    forwarded to logging.handlers.RotatingFileHandler.
    '''
    formatter = kwargs.pop('formatter', DEFAULT_FORMATTER)
    file_level = kwargs.pop('file_level', LOGGER.level)
    if 'maxBytes' not in kwargs:
        kwargs['maxBytes'] = MAX_BYTES
    if 'backupCount' not in kwargs:
        kwargs['backupCount'] = BACKUP_COUNT
    file_handler = RotatingFileHandler(*args, **kwargs)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)
    LOGGER.addHandler(file_handler)
    return LOGGER


def quick_stdout(formatter=DEFAULT_FORMATTER, *args, **kwargs):
    '''Add a standard out stream handler to the logger with the given formatter.
    '''
    stdout_level = kwargs.pop('console_level', LOGGER.level)
    stdout_handler = logging.StreamHandler(*args, **kwargs)
    stdout_handler.setLevel(stdout_level)
#    stdout_handler.setFormatter(formatter)
    LOGGER.addHandler(stdout_handler)
    return LOGGER
