from enum import Enum, auto


class LogLevel(Enum):
    DEBUG = auto()
    INPUT = auto()
    OUTPUT = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()
    FATAL = auto()


class NaveeModule(Enum):
    COUNTERFEIT_BACKEND = auto()
    RISE_UPDATE = auto()
    SPECIFIC_SCRAPER = auto()
    BARINOMI_BACKEND = auto()
    RISE = auto()
    RISE_BETA = auto()
    INFEX_WORKER = auto()
    MODERATION_WORKER = auto()
    INSERTION_WORKER = auto()
    ARCHIVING_WORKER = auto()
    TAKEDOWN_WORKER = auto()
    LOGO_DETECTION_WORKER = auto()
    CATEGORY_CLASSIFICATION_WORKER = auto()
    RISE_RESCORING_WORKER = auto()
    RUSSIAN_RADARLY = auto()
    SNOWBALL_EFFECT = auto()
    GUCCI_GREY_MARKET = auto()
    SCRIPT = auto()
    CRON_JOB = auto()
    TAKEDOWN_REQUEST = auto()
