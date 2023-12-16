# Incremental savers
import concurrent.futures
import logging
import re
import time
from abc import ABC
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from eb_infex_worker.information_extraction import vst
from tqdm import tqdm

log = logging.getLogger(__name__)


class Counter_repeated_action(object):
    """
    Will check whether repeated action should be performed
    """

    def __init__(self, sslice="::", seconds=None, iters=None):
        self.sslice = sslice
        self.seconds = seconds
        self.iters = iters
        self.tic(-1)

    def tic(self, i=None):
        self._time_last = time.perf_counter()
        if i is not None:
            self._i_last = i

    def check(self, i=None):
        ACTION = False
        if i is not None:
            ACTION |= vst.check_step(i, self.sslice)
            if self.iters is not None:
                ACTION |= (i - self._i_last) >= self.iters

        if self.seconds is not None:
            time_since_last = time.perf_counter() - self._time_last
            ACTION |= time_since_last >= self.seconds
        return ACTION


class Isaver_base0(ABC):
    def __init__(self, folder, total):
        self._re_finished = r"item_(?P<i>\d+)_of_(?P<N>\d+).finished"
        self._fmt_finished = "item_{:04d}_of_{:04d}.finished"
        self._history_size = 3

        self._folder = folder
        self._total = total
        if self._folder is None:
            log.debug("Isaver without folder, no saving will be performed")
        else:
            self._folder = vst.mkdir(self._folder)

    def _get_filenames(self, i) -> Dict[str, Path]:
        if self._folder is None:
            raise RuntimeError("Filenames are undefined without folder")
        filenames = {"finished": self._folder / self._fmt_finished.format(i, self._total)}
        return filenames

    def _get_intermediate_files(self) -> Dict[int, Dict[str, Path]]:
        """Check re_finished, query existing filenames"""
        if (self._folder is None) or (not self._folder.exists()):
            return {}
        intermediate_files = {}
        for ffilename in self._folder.iterdir():
            matched = re.match(self._re_finished, ffilename.name)
            if matched:
                i = int(matched.groupdict()["i"])
                # Check if filenames exist
                filenames = self._get_filenames(i)
                all_exist = all([v.exists() for v in filenames.values()])
                assert ffilename == filenames["finished"]
                if all_exist:
                    intermediate_files[i] = filenames
        return intermediate_files

    def _purge_intermediate_files(self):
        if self._folder is None:
            log.debug("Isaver folder is None, no purging")
            return
        """Remove old saved states"""
        intermediate_files: Dict[int, Dict[str, Path]] = self._get_intermediate_files()
        inds_to_purge = np.sort(np.fromiter(intermediate_files.keys(), np.int))[: -self._history_size]
        files_purged = 0
        for ind in inds_to_purge:
            filenames = intermediate_files[ind]
            for filename in filenames.values():
                filename.unlink()
                files_purged += 1
        log.debug("Purged {} states, {} files".format(len(inds_to_purge), files_purged))


class Isaver_base(Isaver_base0):
    result: Any

    def __init__(self, folder, total):
        super().__init__(folder, total)

    def _get_filenames(self, i) -> Dict[str, Path]:
        filenames = super()._get_filenames(i)
        filenames["pkl"] = filenames["finished"].with_suffix(".pkl")
        return filenames

    def _restore(self):
        intermediate_files: Dict[int, Dict[str, Path]] = self._get_intermediate_files()
        start_i, ifiles = max(intermediate_files.items(), default=(-1, None))
        if ifiles is not None:
            restore_from = ifiles["pkl"]
            self.result = vst.load_pkl(restore_from)
            log.debug("Restore from {}".format(restore_from))
        return start_i

    def _save(self, i):
        if self._folder is None:
            log.debug("Isaver folder is None, no saving")
            return
        ifiles = self._get_filenames(i)
        savepath = ifiles["pkl"]
        vst.mkdir(savepath.parent)
        vst.save_pkl(savepath, self.result)
        ifiles["finished"].touch()


class Isaver_simple(Isaver_base):
    """
    Will process a list with a func

    - save_perid: SSLICE spec
    - log_interval, save_inverval: in seconds
    """

    def __init__(
        self,
        folder,
        arg_list,
        func,
        save_period="::",
        save_interval=120,  # every 2 minutes by default
        log_interval=None,
    ):
        super().__init__(folder, len(arg_list))
        self.arg_list = arg_list
        self.result = []
        self.func = func
        self._save_period = save_period
        self._save_interval = save_interval
        self._log_interval = log_interval

    def run(self):
        start_i = self._restore()
        run_range = np.arange(start_i + 1, self._total)
        self._time_last_save = time.perf_counter()
        self._time_last_log = time.perf_counter()
        pbar = tqdm(run_range)
        for i in pbar:
            args = self.arg_list[i]
            self.result.append(self.func(*args))
            # Save check
            SAVE = vst.check_step(i, self._save_period)
            if self._save_interval:
                since_last_save = time.perf_counter() - self._time_last_save
                SAVE |= since_last_save > self._save_interval
            SAVE |= i + 1 == self._total
            if SAVE:
                self._save(i)
                self._purge_intermediate_files()
                self._time_last_save = time.perf_counter()
            # Log check
            if self._log_interval:
                since_last_log = time.perf_counter() - self._time_last_log
                if since_last_log > self._log_interval:
                    log.info(vst.tqdm_str(pbar))
                    self._time_last_log = time.perf_counter()
        return self.result


class Isaver_threading(Isaver_base):
    """
    Will process a list with a func, in async manner
    """

    def __init__(
        self,
        folder,
        arg_list: List[List[Any]],
        func: Callable,
        *,
        save_iters=np.inf,
        save_interval=120,
        max_workers=None,
        progress: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        arg_list = list(arg_list)
        super().__init__(folder, len(arg_list))
        self.arg_list = arg_list
        self.func = func
        self._save_iters = save_iters
        self._save_interval = save_interval
        self._max_workers = max_workers
        self._progress = progress
        self._timeout = timeout
        self.result = {}

    def run(self):
        self._restore()
        countra = Counter_repeated_action(seconds=self._save_interval)

        all_ii = set(range(len(self.arg_list)))
        remaining_ii = all_ii - set(self.result.keys())

        flush_dict = {}

        def flush_purge():
            if not len(flush_dict):
                return
            self.result.update(flush_dict)
            flush_dict.clear()
            self._save(len(self.result))
            self._purge_intermediate_files()

        if self._max_workers == 0:
            # Run with zero threads, for debugging purposes
            pbar = remaining_ii
            if self._progress:
                pbar = tqdm(pbar, self._progress)
            for i in pbar:
                result = self.func(*self.arg_list[i])
                flush_dict[i] = result
                if countra.check() or len(flush_dict) >= self._save_iters:
                    flush_purge()
                    countra.tic()
        else:
            # Proper threading run
            io_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers)
            io_futures = []
            for i in remaining_ii:
                args = self.arg_list[i]
                submitted = io_executor.submit(self.func, *args)
                submitted.i = i
                io_futures.append(submitted)
            pbar = concurrent.futures.as_completed(io_futures)
            if self._progress:
                pbar = tqdm(pbar, self._progress, total=len(io_futures))
            for io_future in pbar:
                result = io_future.result(timeout=self._timeout)
                i = io_future.i
                flush_dict[i] = result
                # A bit dirty, but should still work
                if countra.check() or len(flush_dict) >= self._save_iters:
                    flush_purge()
                    countra.tic()

        flush_purge()
        assert len(self.result) == len(self.arg_list)
        result_list = [self.result[i] for i in all_ii]
        return result_list


class Isaver_dataloader(Isaver_base):
    """
    Will process a list with a 'func',
    - prepare_func(start_i) is to be run before processing

    Example:
        def prepare_func(i_last):
            dset = creator_tdata_eval(negatives_cvt[i_last+1:])
            dload = creator_dload_eval(dset)
            return dload

        def func(data_input):
            data, target, meta = helper_metamodel.data_preprocess(data_input)
            data, target = map(lambda x: x.to(device), (data, target))
            with torch.no_grad():
                output = helper_metamodel.get_eval_output(data, meta)
            score_np = output.detach().cpu().numpy()
            inds = [x['item']['ind'] for x in meta]
            result_dict = {'score': score_np, 'ind': inds}
            i_last = negatives_inds.index(inds[-1])
            return result_dict, i_last
    """

    def __init__(
        self,
        folder,
        total,
        func,
        prepare_func,
        *,
        save_period="::",
        save_interval=120,
        log_interval=None,
        progress: Optional[str] = None
    ):
        super().__init__(folder, total)
        self.func = func
        self.prepare_func = prepare_func
        self._save_period = save_period
        self._save_interval = save_interval
        self._log_interval = log_interval
        self._progress = progress
        self.result = []

    def run(self):
        i_last = self._restore()
        countra = Counter_repeated_action(sslice=self._save_period, seconds=self._save_interval)

        result_cache = []

        def flush_purge():
            if not len(result_cache):
                return
            self.result.extend(result_cache)
            result_cache.clear()
            self._save(i_last)
            self._purge_intermediate_files()

        loader = self.prepare_func(i_last)
        pbar = enumerate(loader)
        if self._progress:
            pbar = tqdm(pbar, self._progress, total=len(loader))
        for i_batch, data_input in pbar:
            result_dict, i_last = self.func(data_input)
            result_cache.append(result_dict)
            if countra.check(i_batch):
                flush_purge()
                if self._progress:
                    log.debug(vst.tqdm_str(pbar))
                countra.tic(i_batch)
        flush_purge()
        return self.result
