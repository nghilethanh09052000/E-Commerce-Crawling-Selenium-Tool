"""
Module with small snippets
"""
import io
import itertools
import json
import logging
import pickle
import platform
import random
import re
import string
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from timeit import default_timer as timer
from typing import Callable, Iterable, List, TypeVar, Union

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

T = TypeVar("T")


"""
Filesystem:
- mkdir, pickle helpers, stashing magic
"""


def mkdir(directory) -> Path:
    """
    Python 3.5 pathlib shortcut to mkdir -p
    Fails if parent is created by other process in the middle of the call
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_json(filepath, obj):
    with Path(filepath).open("w") as f:
        json.dump(obj, f, indent=4, sort_keys=True)


def load_json(filepath):
    with Path(filepath).open("r") as f:
        obj = json.load(f)
    return obj


def save_pkl(filepath, obj):
    with Path(filepath).open("wb") as f:
        pickle.dump(obj, f)


def load_pkl(filepath):
    with Path(filepath).resolve().open("rb") as f:
        obj = pickle.load(f)
    return obj


def load_pkl_whichever(*filepaths):
    """Try to unpickle any file from the list"""
    for filepath in filepaths:
        try:
            with Path(filepath).resolve().open("rb") as f:
                pkl = pickle.load(f)
            return pkl
        except (FileNotFoundError, IsADirectoryError) as err:
            log.debug(f"Skipping.. Failed to load {filepath}. Error {err}")
    raise FileNotFoundError("Failed to load pkl from a list of files", list(filepaths))


def load_py2_pkl(filepath):
    with Path(filepath).resolve().open("rb") as f:
        pkl = pickle.load(f, encoding="latin1")
    return pkl


def compute_or_load_pkl(filepath: Union[str, Path], function: Callable[..., T], *args, **kwargs) -> T:
    """
    Bread and butter of checkpoints
    - If filepath exists - try to load it
    - If filepath does not exist or failed to load - launch function
    """
    filepath = Path(filepath)
    start = timer()
    try:
        with filepath.open("rb") as f:
            pkl_bytes = f.read()
            pkl = pickle.loads(pkl_bytes)
        log.debug(f"Unpickled {filepath} in {timer() - start:.2f}s")
    except (EOFError, FileNotFoundError) as e:
        log.debug(f'Caught "{e}" error, Computing {function}(*args, **kwargs)')
        pkl = function(*args, **kwargs)
        with filepath.open("wb") as f:
            pickle.dump(pkl, f, pickle.HIGHEST_PROTOCOL)
        log.debug(f"Computed and pickled to {filepath} in {timer() - start:.2f}s")
    return pkl


def compute_or_load_pkl_silently(filepath: Union[str, Path], function: Callable[..., T], *args, **kwargs) -> T:
    """Implementation without outputs"""
    try:
        with Path(filepath).open("rb") as f:
            pkl = pickle.load(f)
    except (EOFError, FileNotFoundError):
        pkl = function(*args, **kwargs)
        with Path(filepath).open("wb") as f:
            pickle.dump(pkl, f, pickle.HIGHEST_PROTOCOL)
    return pkl


def stash2(stash_to, *, active=True, silent=False) -> Callable:
    if silent:
        c_pkl_func = compute_or_load_pkl_silently
    else:
        c_pkl_func = compute_or_load_pkl
    if active:

        def stash_func(function, *args, **kwargs):
            return c_pkl_func(stash_to, function, *args, **kwargs)

    else:

        def stash_func(function, *args, **kwargs):
            return function(*args, **kwargs)

    return stash_func


"""
Context Managers
"""


@contextmanager
def np_printoptions(*args, **kwargs):
    """Temporary set numpy printoptions
    with np_printoptions(precision=3, suppress=True):
    http://stackoverflow.com/questions/2891790/pretty-printing-of-numpy-array
    """
    original = np.get_printoptions()
    np.set_printoptions(*args, **kwargs)
    yield
    np.set_printoptions(**original)


class QTimer(object):
    """
    Example:

    with QTimer('Creating roidbs took %(time) sec'):
        or
    with QTimer('Long task'):
    """

    def __init__(self, message=None, enabled=True):
        self.message = message
        self.enabled = enabled

    def __enter__(self):
        self.start = timer()
        # // Get parent stack info
        f = sys._getframe(1)  # Get parent frame
        if hasattr(f, "f_code"):
            co = f.f_code
            _file = co.co_filename.split("/")[-1]
            _line = f.f_lineno
            _function = co.co_name
        else:
            _file, _line, _function = ("(unknown file)", 0, "(unknown function)")
        self.stack_info_str = f"{_file}({_line}){_function}: "
        return self

    def __exit__(self, *args):
        self.end = timer()
        self.time = self.end - self.start

        if self.message and self.enabled:
            message = self.message
            if "%(time)" not in message:
                message += " took %(time) sec"
            message = self.stack_info_str + message.replace("%(time)", f"{self.time:.2f}")
            log.info(message)


"""
Table creation
"""


def string_table(
    table_rows: List[Iterable],
    header: List[str] = None,
    col_formats: Iterable[str] = itertools.repeat("{}"),
    col_alignments: Iterable[str] = itertools.repeat("<"),
    pad=0,
) -> str:
    """Revisiting the string tables creation"""
    table_rows_s = [[cf.format(i) for i, cf in zip(row, col_formats)] for row in table_rows]
    if header is not None:
        table_rows_s = [header] + table_rows_s
    widths = []
    for x in zip(*table_rows_s):
        widths.append(max([len(y) for y in x]))
    formats = [f"{{:{a}{w}}}" for w, a in zip(widths, col_alignments)]
    formats = [f"{f:^{pad+len(f)}}" for f in formats]  # Apply padding
    row_format = "|" + "|".join(formats) + "|"
    table = [row_format.format(*row) for row in table_rows_s]
    return "\n".join(table)


def df_to_table(df: pd.DataFrame, indexcols=None) -> str:
    # Header
    if indexcols is None:
        if isinstance(df.index, pd.MultiIndex):
            indexnames = df.index.names
        else:
            indexnames = [
                df.index.name,
            ]
        indexcols = []
        for i, n in enumerate(indexnames):
            iname = n if n else f"ix{i}"
            indexcols.append(iname)
    header = indexcols + [str(x) for x in df.columns]
    # Col formats
    col_formats = ["{}"] * len(indexcols)
    for dt in df.dtypes:
        form = "{}"
        if dt in ["float32", "float64"]:
            form = "{:.2f}"
        col_formats.append(form)

    table = string_table(np.array(df.reset_index()), header=header, col_formats=col_formats, pad=2)  # type: ignore
    return table


"""
Logging
"""


reasonable_formatters = {
    "extended": logging.Formatter("%(asctime)s %(name)s %(funcName)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"),
    "short": logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"),
    "shortest": logging.Formatter("%(asctime)s: %(message)s", "%Y-%m-%d %H:%M:%S"),
}


@contextmanager
def logging_disabled(disable_level=logging.CRITICAL):
    """Temporarily disable logging inside context
    http://stackoverflow.com/questions/2266646/how-to-i-disable-and-re-enable-console-logging-in-python
    """
    logging.disable(disable_level)
    yield
    logging.disable(logging.NOTSET)


class CaptureLogRecordsHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.captured_records = []

    def emit(self, record):
        self.captured_records.append(record)

    def close(self):
        logging.Handler.close(self)


class LogCaptorToRecords(object):
    def __init__(self, pause_others=False):
        self.pause_others = pause_others
        self._logger = logging.getLogger()
        self._captor_handler = CaptureLogRecordsHandler()
        self.captured = []

    def _pause_other_handlers(self):
        self._other_handlers = self._logger.handlers.copy()
        for handle in self._logger.handlers:
            self._logger.removeHandler(handle)

    def _unpause_other_handlers(self):
        for handle in self._other_handlers:
            self._logger.addHandler(handle)

    def __enter__(self):
        if self.pause_others:
            self._pause_other_handlers()
        self._logger.addHandler(self._captor_handler)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.pause_others:
            self._unpause_other_handlers()
        self._logger.removeHandler(self._captor_handler)
        self.captured = self._captor_handler.captured_records[:]
        # If exception was raise - handle captured right now
        if exc_type is not None:
            log.error("<<(CAPTURED BEGIN)>> Capturer encountered an " "exception and released captured records")
            self.handle_captured()
            log.error("<<(CAPTURED END)>> End of captured records")

    def handle_captured(self):
        for record in self.captured:
            self._logger.handle(record)


class LogCaptorToString(object):
    def __init__(self, loglevel=logging.DEBUG, pause_other_handlers=False):

        self.loglevel = loglevel
        self.pause_other_handlers = pause_other_handlers
        self._logger = logging.getLogger()

    def __enter__(self):
        self._log_capture_string = io.StringIO()
        if self.pause_other_handlers:
            self._other_handlers = self._logger.handlers.copy()
            for handle in self._logger.handlers:
                self._logger.removeHandler(handle)
        self._temporary_stream_handler = logging.StreamHandler(self._log_capture_string)
        self._temporary_stream_handler.setLevel(self.loglevel)
        self._logger.addHandler(self._temporary_stream_handler)
        return self

    def __exit__(self, *args):
        self.captured = self._log_capture_string.getvalue()
        self._logger.removeHandler(self._temporary_stream_handler)
        if self.pause_other_handlers:
            for handle in self._other_handlers:
                self._logger.addHandler(handle)


def add_filehandler(logfilename, level=logging.DEBUG, formatter="extended"):
    if isinstance(formatter, str):
        formatter = reasonable_formatters[formatter]
    out_filehandler = logging.FileHandler(str(logfilename))
    out_filehandler.setFormatter(formatter)
    out_filehandler.setLevel(level)
    logging.getLogger().addHandler(out_filehandler)
    return logfilename


def reasonable_logging_setup(stream_loglevel: int, formatter="extended"):
    """Create STDOUT stream handler, curtail spam"""
    if isinstance(formatter, str):
        formatter = reasonable_formatters[formatter]
    # Get root logger (with NOTSET level)
    logger = logging.getLogger()
    logger.setLevel(logging.NOTSET)
    # Stream handler takes 'loglevel'
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(stream_loglevel)
    logger.addHandler(handler)
    # Prevent some spammy packages from exceeding INFO verbosity
    spammy_packages = ["PIL", "git", "tensorflow", "matplotlib", "selenium", "urllib3"]
    for packagename in spammy_packages:
        logging.getLogger(packagename).setLevel(max(logging.INFO, stream_loglevel))
    return logger


def quick_log_setup(level):
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def additional_logging(rundir):
    # Also log to rundir
    id_string = get_experiment_id_string()
    logfilename = mkdir(rundir) / "{}.log".format(id_string)
    out_filehandler = logging.FileHandler(str(logfilename))
    LOG_FORMATTER = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    out_filehandler.setFormatter(LOG_FORMATTER)
    out_filehandler.setLevel(logging.INFO)
    logging.getLogger().addHandler(out_filehandler)


"""
Various simple snippets
"""


class Averager(object):
    """
    Taken from kensh code. Also seen in Gunnar's code
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.last = 0.0
        self.avg = 0.0
        self._sum = 0.0
        self._count = 0.0

    def update(self, value, weight=1):
        self.last = value
        self._sum += value * weight
        self._count += weight
        self.avg = self._sum / self._count

    def __repr__(self):
        return "Averager[{:.4f} (A: {:.4f})]".format(self.last, self.avg)


def is_venv():
    # https://stackoverflow.com/questions/1871549/determine-if-python-is-running-inside-virtualenv
    return hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)


def add_pypath(path):
    path = str(path)  # To cover pathlib strings
    if path not in sys.path:
        sys.path.insert(0, path)


def check_step(step: int, period_sslice: str) -> bool:
    """
    Check whether step matches SSLICE spec

    SSLICE spec: '(more_runs):(run_limit):(period)'
      - more_runs: (csv list of runs when we should fire)
      - run_limit: [MIN],[MAX] (inclusive, don't fire beyond)
      - period: (fire at period intervals)
    """
    spec_re = r"^([\d,]*):((?:\d*,\d*)?):([\d]*)$"
    match = re.fullmatch(spec_re, period_sslice)
    if match is None:
        raise ValueError(f"Invalid spec {period_sslice}")
    _more_runs, run_limit, _period = match.groups()

    if len(run_limit):
        lmin, lmax = run_limit.split(",")
        if lmin and step < int(lmin):
            return False
        if lmax and step > int(lmax):
            return False
    if _more_runs and step in map(int, _more_runs.split(",")):
        return True
    if _period and step and (step % int(_period) == 0):
        return True
    return False


def tqdm_str(pbar, ninc=0):
    if pbar is None:
        tqdm_str = ""
    else:
        tqdm_str = "TQDM[" + pbar.format_meter(pbar.n + ninc, pbar.total, pbar._time() - pbar.start_t) + "]"
    return tqdm_str


def get_experiment_id_string():
    time_now = datetime.now()
    str_time = time_now.strftime("%Y-%m-%d_%H-%M-%S")
    str_ms = time_now.strftime("%f")
    str_rnd = str_ms[:3] + "".join(random.choices(string.ascii_uppercase, k=3))
    str_node = platform.node()
    return f"{str_time}_{str_rnd}_{str_node}"


def leqn_split(arr, N):
    """Divide 1d np array into batches of len <= N"""
    return np.array_split(arr, (len(arr) - 1) // N + 1)
