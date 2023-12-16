from time import time
import inspect
import re
import logging
from uuid import uuid4
from functools import wraps
import sys
import random
import string

import boto3

# Sentry does not need to be initialized. It is initialized by the main app
import sentry_sdk

from navee_logging.enums import LogLevel, NaveeModule
from navee_logging import watchtower
from threading import get_ident

alphabet = string.ascii_lowercase + string.digits

SCRIPT_LOG_GROUP = "navee/scripts"


class NoStyleFormatter(logging.Formatter):
    # Remove ANSI escape codes
    format_regex = r"\033\[[0-9;]*[mG]"

    def __init__(self, fmt=None, datefmt=None, style="%", validate=True):
        fmt = re.sub(self.format_regex, "", fmt)
        super().__init__(fmt, datefmt, style, validate)

    def format(self, record):
        record.msg = re.sub(self.format_regex, "", record.msg)
        return super().format(record)


class NaveeLoggerMeta(type):
    _instances = {}

    def __call__(cls, *args, override=False, **kwargs):
        if (
            get_ident() not in cls._instances
            or override
            or cls._instances[get_ident()].module is None
        ):
            instance = super().__call__(*args, **kwargs)
            cls._instances[get_ident()] = instance
        return cls._instances[get_ident()]


def use_current(f):
    @wraps(f)
    def wrapper(self, *args, skip=False, **kwargs):
        if skip:
            return f(self, *args, **kwargs)
        else:
            if get_ident() not in type(NaveeLogger)._instances:
                type(NaveeLogger)._instances[get_ident()] = NaveeLogger(
                    module=self.module,
                    aws_access_key=self.aws_access_key,
                    aws_secret_key=self.aws_secret_key,
                    aws_region=self.aws_region,
                    environment=self.environment,
                    dev=self.dev,
                )

            current = type(NaveeLogger)._instances[get_ident()]
            if current and self and self != current:
                return getattr(current, f.__name__)(*args, **kwargs)
            else:
                return getattr(self, f.__name__)(*args, **kwargs, skip=True)

    return wrapper


def for_all_methods(exclude, decorator):
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)) and attr not in exclude:
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate


@for_all_methods(
    ["__init__", "create_script_logger", "create_default_logger"], use_current
)
class NaveeLogger(metaclass=NaveeLoggerMeta):
    def __init__(
        self,
        module: NaveeModule = None,
        aws_access_key=None,
        aws_secret_key=None,
        aws_region=None,
        environment=None,
        dev=False,
    ) -> None:
        self.call_start_time = None
        self.call_name = None
        self.call_id = None
        self.module = module
        self.environment = environment
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_region = aws_region
        self.dev = dev

        if module == NaveeModule.SCRIPT:
            self.logger = self.create_script_logger(
                aws_access_key, aws_secret_key, aws_region
            )
        elif module:
            self.logger = self.create_default_logger()

    def create_default_logger(self):
        # Formatter for the loggers
        Formatter = logging.Formatter if sys.stdout.isatty() else NoStyleFormatter
        formatter = Formatter(
            "\033[2m\033[36m[%(asctime)s] %(_module)s\033[0m %(loglevel)s\t%(message)s\t\t\033[35m\033[2m%(others)s \033[0m\033[2mcall_id=%(call_id)s %(processName)s:%(process)d %(_filename)s:ln%(line_number)s:%(function_name)s()\033[0m",
            datefmt="%Y-%m-%d %H:%M:%S%z",
        )

        # Default logger
        default_handler = logging.StreamHandler(sys.stdout)
        default_handler.setFormatter(formatter)

        default_logger = logging.getLogger(str(uuid4()))
        default_logger.setLevel(logging.DEBUG)
        default_logger.addHandler(default_handler)

        default_logger.propagate = False

        return default_logger

    def create_script_logger(self, aws_access_key, aws_secret_key, aws_region):
        # Formatter for the loggers
        Formatter = logging.Formatter if sys.stdout.isatty() else NoStyleFormatter
        formatter = Formatter(
            "\033[2m\033[36m[%(asctime)s] %(_module)s\033[0m %(loglevel)s\t%(message)s\t\t\033[35m\033[2m%(others)s \033[0m\033[2mcall_id=%(call_id)s %(processName)s:%(process)d %(_filename)s:ln%(line_number)s:%(function_name)s()\033[0m",
            datefmt="%Y-%m-%d %H:%M:%S%z",
        )

        # Default logger
        default_handler = logging.StreamHandler()
        default_handler.setFormatter(formatter)

        # Script logger
        boto3_client = boto3.client(
            "logs",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region,
        )

        script_handler = watchtower.CloudWatchLogHandler(
            log_group_name=SCRIPT_LOG_GROUP,
            boto3_client=boto3_client,
        )
        script_handler.setFormatter(formatter)

        script_logger = logging.getLogger(str(uuid4()))
        script_logger.setLevel(logging.DEBUG)

        script_logger.addHandler(script_handler)
        script_logger.addHandler(default_handler)
        script_logger.propagate = False

        return script_logger

    def debug(self, message, **kwargs):
        """Custom navee logger

        Args:
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """
        self.log(LogLevel.DEBUG, message, **kwargs)

    def input(self, message, call_name=None, **kwargs):
        """Custom navee logger

        Args:
            call_name (str): Name of the route, script, cron, etc.
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """

        if (
            self.call_start_time is not None
            or self.call_id is not None
            or self.call_name is not None
        ):
            print(
                "WARNING: input logging has been called without calling output previously"
            )

        self.call_start_time = time()
        self.call_id = uuid4()
        self.call_name = call_name

        self.log(LogLevel.INPUT, message, **kwargs)

    def output(self, message, **kwargs):
        """Custom navee logger

        Args:
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """

        self.log(LogLevel.OUTPUT, message, **kwargs)

        if self.call_start_time is None or self.call_id is None:
            print(
                "WARNING: output logging has been called without calling input previously"
            )

        self.call_start_time = None
        self.call_id = None
        self.call_name = None

    def info(self, message, **kwargs):
        """Custom navee logger # Remove ANSI escape codes from the log message

        Args:
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """
        self.log(LogLevel.INFO, message, **kwargs)

    def warn(self, message, **kwargs):
        """Custom navee logger

        Args:
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """
        self.log(LogLevel.WARNING, message, **kwargs)

    def warning(self, message, **kwargs):
        """Custom navee logger

        Args:
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """
        self.log(LogLevel.WARNING, message, **kwargs)

    def handle_error(self, message, loglevel, **kwargs):
        exc_type, exc_value, _ = sys.exc_info()
        if exc_type is None:
            self.log(loglevel, message, **kwargs)
        else:
            self.exception(message, exc_value, **kwargs)

    def error(self, message, **kwargs):
        """Custom navee logger

        Args:
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """
        self.handle_error(message, LogLevel.ERROR, **kwargs)

    def critical(self, message, **kwargs):
        """Custom navee logger

        Args:
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """
        self.handle_error(message, LogLevel.CRITICAL, **kwargs)

    def fatal(self, message, **kwargs):
        """Custom navee logger

        Args:
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """
        self.handle_error(message, LogLevel.FATAL, **kwargs)

    def exception(self, message, exc, **kwargs):
        with sentry_sdk.push_scope() as scope:
            for key, value in {**kwargs}.items():
                scope.set_extra(key, value)
            scope.set_extra("Log message", message)
            sentry_sdk.capture_exception(exc)

        self.log(LogLevel.WARNING, f"{message} {repr(exc)=}", **kwargs)

    def log(
        self,
        loglevel,
        message,
        status_code=None,
        post_link=None,
        post_id=None,
        user_id=None,
        user_email=None,
        organisation_id=None,
        organisation_name=None,
        image_id=None,
        image_link=None,
        duplicated_group_id=None,
        poster_id=None,
        poster_name=None,
        website_id=None,
        domain_name=None,
        method=None,
        entity=None,
        entity_id=None,
    ):
        """Custom navee logger

        Args:
            loglevel (LogLevel): Level of the log
            message (str): Message to log
            status_code (str, optional): Status of the HTTP response. Defaults to None.
            post_link (str, optional): Link of the related post. Defaults to None.
            post_id (int, optional): Id of the related post. Defaults to None.
            user_id (int, optional): Id of the related user. Defaults to None.
            user_email (str, optional): Email of the related user. Defaults to None.
            organisation_id (int, optional): Id of the related organisation. Defaults to None.
            organisation_name (str, optional): Name of the related organisation. Defaults to None.
            image_id (int, optional): Id of the related image. Defaults to None.
            image_link (str, optional): Link of the related image. Defaults to None.
            duplicated_group_id (str, optional): If of the related duplicated group. Defaults to None.
            poster_id (int, optional): Id if the related poster. Defaults to None.
            poster_name (str, optional): Name of the related poster. Defaults to None.
            website_id (int, optional): Id of the related website. Defaults to None.
            domain_name (str, optional): Domain name of the related website. Defaults to None.
            method (str, optional): Strategy used to determine result of the function. Defaults to None
            entity (str, optional): Entity concerned by the log. Defaults to None.
            entity_id (int, optional): Id of the entity. Defaults to None.
        """
        if self.call_start_time is None or self.call_id is None:
            print(
                f"WARNING: {loglevel} logging has been called without calling input previously"
            )
            self.call_start_time = time()
            self.call_id = "".join(random.choices(alphabet, k=8))

        if self.call_name is None:
            print("WARNING: call_name is None.")
            self.call_name = ""

        duration = time() - self.call_start_time

        # Format optional fields
        others = ""
        argspec = inspect.getfullargspec(self.log.__wrapped__)
        for kwarg in argspec.args[-len(argspec.defaults) :]:
            if locals()[kwarg]:
                others += f" {kwarg}={locals()[kwarg]}"
        if self.call_name:
            others += f" call_name={self.call_name}"
            others += f" duration={duration:f}"

        # Get caller info
        previous_frame = inspect.currentframe().f_back
        filename = "/navee_logging/logger.py"
        while filename.endswith("/navee_logging/logger.py"):
            previous_frame = previous_frame.f_back
            (filename, line_number, function_name, _, _) = inspect.getframeinfo(
                previous_frame
            )

        log_level_to_log_fn = {
            LogLevel.DEBUG: self.logger.debug,
            LogLevel.INFO: self.logger.info,
            LogLevel.WARNING: self.logger.warn,
            LogLevel.ERROR: self.logger.error,
            LogLevel.CRITICAL: self.logger.critical,
            LogLevel.FATAL: self.logger.fatal,
            LogLevel.INPUT: self.logger.debug,
            LogLevel.OUTPUT: self.logger.debug,
        }

        if not sys.stdout.isatty():
            loglevel_name = loglevel.name
        elif loglevel == LogLevel.WARNING:
            loglevel_name = f"\033[33m{loglevel.name}\033[0m"
        elif loglevel == LogLevel.ERROR:
            loglevel_name = f"\033[1m\033[31m{loglevel.name}\033[0m"
        elif loglevel == LogLevel.CRITICAL:
            loglevel_name = f"\033[41m\033[1m\033[37m{loglevel.name}\033[0m"
        else:
            loglevel_name = f"\033[34m{loglevel.name}\033[0m"

        log_level_to_log_fn[loglevel](
            message,
            extra={
                "_module": self.module.name,
                "loglevel": loglevel_name,
                "others": others,
                "_filename": filename,
                "line_number": line_number,
                "function_name": function_name,
                "call_id": self.call_id,
            },
        )
