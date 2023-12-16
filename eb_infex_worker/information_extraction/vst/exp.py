#!/usr/bin/env python3
import collections
import copy
import importlib
import itertools
import logging
import pprint
import re
from pathlib import Path
from typing import List, Optional

import numpy as np
import yaml
from docopt import docopt
from . import small

log = logging.getLogger(__name__)


def get_subfolders(folder, subfolder_names=["out", "temp"]):
    return [small.mkdir(folder / name) for name in subfolder_names]


def set_dd(d, key, value, sep=".", soft=False):
    """Dynamic assignment to nested dictionary
    http://stackoverflow.com/questions/21297475/set-a-value-deep-in-a-dict-dynamically"""
    dd = d
    keys = key.split(sep)
    latest = keys.pop()
    for k in keys:
        dd = dd.setdefault(k, {})
    if soft:
        dd.setdefault(latest, value)
    else:
        dd[latest] = value


def gir_merge_dicts(user, default):
    """Girschik's dict merge from F-RCNN python implementation"""
    if isinstance(user, dict) and isinstance(default, dict):
        for k, v in default.items():
            if k not in user:
                user[k] = v
            else:
                user[k] = gir_merge_dicts(user[k], v)
    return user


def unflatten_nested_dict(flat_dict, sep="."):
    nested = {}
    for k, v in flat_dict.items():
        set_dd(nested, k, v, sep)
    return nested


def flatten_nested_dict(d, parent_key="", sep="."):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.abc.MutableMapping):
            items.extend(flatten_nested_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


class ConfigLoader(yaml.SafeLoader):
    pass


class Ydefault(yaml.YAMLObject):
    yaml_tag = "!def"
    argnames = ("default", "values", "typecheck", "evalcheck")
    yaml_loader = [ConfigLoader]

    def __init__(
        self,
        default=None,
        values: Optional[List] = None,
        typecheck=None,
        evalcheck: str = None,
    ):
        self.default = default
        self.values = values
        self.typecheck = typecheck
        self.evalcheck = evalcheck

    @classmethod
    def from_yaml(cls, loader, node):
        """
        If scalar: assume this is default
        If sequence: assume correspondence to
            [default, values, typecheck, evalcheck]
        if mapping: feed to the constructor directly
        """
        args = {}
        if isinstance(node, yaml.MappingNode):
            x = loader.construct_mapping(node, deep=True)
            for k, v in x.items():
                if k in cls.argnames:
                    args[k] = v
        elif isinstance(node, yaml.SequenceNode):
            x = loader.construct_sequence(node, deep=True)
            for k, v in zip(cls.argnames, x):
                if v is not None:
                    args[k] = v
        elif isinstance(node, yaml.ScalarNode):
            args["default"] = loader.construct_scalar(node)
        else:
            raise RuntimeError()
        ydef = Ydefault(**args)
        return ydef

    def __repr__(self):
        items = [str(self.default)]
        for arg in self.argnames[1:]:
            attr = getattr(self, arg, None)
            if attr is not None:
                items.append(f"{arg}: {attr}")
        s = "Ydef[{}]".format(", ".join(items))
        return s


# ConfigLoader.add_constructor('!def', Ydefault)


def _flat_config_merge(merge_into, merge_from, prefix, allow_overwrite):
    assert isinstance(prefix, str)
    for k, v in merge_from.items():
        key = f"{prefix}{k}"
        if key in merge_into and not allow_overwrite:
            raise ValueError("key {} already in {}".format(key, merge_into))
        merge_into[key] = v


def _config_assign_defaults(cf, cf_defaults, allowed_wo_defaults=[], raise_without_defaults=True):
    # // Assign defaults
    cf_with_defaults = copy.deepcopy(cf)
    assert isinstance(allowed_wo_defaults, list), "Wrong spec for allowed_wo_defaults"

    keys_cf = np.array(list(cf.keys()))
    keys_cf_default = np.array(list(cf_defaults.keys()))
    DEFAULTS_ASSIGNED = []

    # // Are there new keys that were not present in default?
    keys_without_defaults = keys_cf[~np.in1d(keys_cf, keys_cf_default)]
    # Take care of keys that were allowed
    allowed_keys_without_defaults = []
    forbidden_keys_without_defaults = []
    for k in keys_without_defaults:
        allowed = False
        for allowed_prefix in allowed_wo_defaults:
            if k.startswith(allowed_prefix):
                allowed = True
        if allowed:
            allowed_keys_without_defaults.append(k)
        else:
            forbidden_keys_without_defaults.append(k)
    if len(allowed_keys_without_defaults):
        log.info("Some keys were allowed to " "exist without defaults: {}".format(allowed_keys_without_defaults))
    # Complain about forbidden ones
    if len(forbidden_keys_without_defaults):
        for k in forbidden_keys_without_defaults:
            log.info(f"ERROR: Key {k} has no default value")
        if raise_without_defaults:
            raise ValueError("Keys without defaults")

    # Are there defaults that need to be assigned
    defaults_without_keys = keys_cf_default[~np.in1d(keys_cf_default, keys_cf)]
    if len(defaults_without_keys):
        for k in defaults_without_keys:
            old_value = cf_with_defaults.get(k)
            new_value = cf_defaults[k]
            cf_with_defaults[k] = new_value
            DEFAULTS_ASSIGNED.append((k, old_value, new_value))

    # Are there None values in final config?
    if None in cf_with_defaults.values():
        none_keys = [k for k, v in cf_with_defaults.items() if v is None]
        log.warning('Config keys {} have "None" value after default merge'.format(none_keys))

    if len(DEFAULTS_ASSIGNED):
        DEFAULTS_TABLE = small.string_table(DEFAULTS_ASSIGNED, header=["KEY", "OLD", "NEW"])
        DEFAULTS_ASSIGNED_STR = "We assigned some defaults:\n{}".format(DEFAULTS_TABLE)
        log.info(DEFAULTS_ASSIGNED_STR)
    cf = cf_with_defaults
    return cf


class YConfig(object):
    """
    Improved, simplified version of YConfig
    - Helps with validation and default params
    - All configurations stored inside are flat
    """

    def __init__(self, cfg_dict, allowed_wo_defaults=[], raise_without_defaults=True):
        """
        - allowed_wo_defaults - Key substrings that are allowed to exist
          without defaults
        """
        self.cf = flatten_nested_dict(cfg_dict)
        self.ydefaults = {}
        self.allowed_wo_defaults = allowed_wo_defaults
        self.raise_without_defaults = raise_without_defaults

    def set_defaults_yaml(self, merge_from: str, prefix="", allow_overwrite=False):
        """Set defaults from YAML string"""
        assert isinstance(merge_from, str)
        yaml_loaded = yaml.load(merge_from, ConfigLoader)
        if not yaml_loaded:
            return
        loaded_flat = flatten_nested_dict(yaml_loaded)
        # Convert everything to Ydefault
        for k, v in loaded_flat.items():
            if not isinstance(v, Ydefault):
                loaded_flat[k] = Ydefault(default=v)
        # Merge into Ydefaults
        _flat_config_merge(self.ydefaults, loaded_flat, prefix, allow_overwrite)

    @staticmethod
    def _check_types(cf, ydefaults):
        for k, v in ydefaults.items():
            assert k in cf, f"Parsed key {k} not in {cf}"
            VALUE = cf[k]
            # Values check
            if v.values is not None:
                assert VALUE in v.values, f"Value {VALUE} for key {k} not in {v.values}"
            # Typecheck
            if v.typecheck is not None:
                good_cls = eval(v.typecheck)
                assert isinstance(VALUE, good_cls), f"Value {VALUE} for key {k} not of type {good_cls}"
            # Evalcheck
            if v.evalcheck is not None:
                assert eval(v.evalcheck) is True, f"Value {VALUE} for key {k} does not eval: {v.evalcheck}"

    def parse(self):
        # remove ignored fields
        self.cf = {k: v for k, v in self.cf.items() if v != "!ignore"}
        cf_defaults = {k: v.default for k, v in self.ydefaults.items()}
        self.cf = _config_assign_defaults(self.cf, cf_defaults, self.allowed_wo_defaults, self.raise_without_defaults)
        self._check_types(self.cf, self.ydefaults)
        return self.cf

    def without_prefix(self, prefix, flat=True):
        new_cf = {}
        for k, v in self.cf.items():
            if k.startswith(prefix):
                new_k = k[len(prefix) :]
                new_cf[new_k] = v
        if not flat:
            new_cf = unflatten_nested_dict(new_cf)
        return new_cf


# Launching dervo scripts without dervo


def expand_relative_path(config_path, value):
    """
    Two kinds of relative paths supported py@anygrab and py@str

    Relative paths have these ugly formats from dervo
        - anygrab:  "py@anygrab(epath/'RPATH', 'SUBPATH'"
        - str: "py@str(epath/'RPATH')"

    Examples:
      - py@anygrab(epath/'../110_retrieve_moncler', 'out/imlogo_list.pkl')
    """
    epath = config_path.parent
    if value.startswith("py@anygrab"):
        # This anygrab overload has two inputs
        match = re.match(r"py@anygrab\(epath/'(.*?)', *'(.*?)'", value)
        if not match:
            match = re.match(r'py@anygrab\(epath/"(.*?)", *"(.*?)"', value)
        if match:
            rpath, subpath = match.groups()
            abspath = str((epath / rpath / subpath).resolve())
            return abspath
        # This anygrab overload has one input
        match = re.match(r"py@anygrab\(epath/'(.*?)'", value)
        if not match:
            match = re.match(r'py@anygrab\(epath/"(.*?)"', value)
        if match:
            rpath = match.group(1)
            abspath = str((epath / rpath).resolve())
            return abspath
        else:
            raise RuntimeError("Wrong format for anygrab")

    elif value.startswith("py@str"):
        match = re.match(r"py@str\(epath/'(.*)'\)", value)
        rpath = match.group(1)
        abspath = str((epath / rpath).resolve())
    else:
        raise RuntimeError("Wrong format for relative path")
    return abspath


DERVO_DOC = """
Run dervo experiments without using the whole experimental system

Usage:
    run_experiment.py --configs <configs_csv> [options]

Options:
    --output_folder <str>     Where outputs will be stored.
                                If not set - same folder as last config_csv
    --experiment_name <str>   Name of experiment.
                                If not set - will pick up "dervo.yml" from the
                                folder of last config_csv
    --experiment_prefix <str>
"""


def dervo_run(args):
    # / Read arguments
    configs_csv = args["<configs_csv>"]
    # // Read configs csv, if folder - assumg cfg.yml is inside
    config_paths = []
    for config_path in configs_csv.split(","):
        config_path = Path(config_path)
        if config_path.is_dir():
            config_path = config_path / "cfg.yml"
        config_paths.append(config_path)
    log.info("Following configs will be loaded: {}".format(pprint.pformat(config_paths)))
    last_config_folder = Path(config_paths[-1]).parent

    # // If output folder not set - assume folder of last config
    output_folder = args.get("--output_folder")
    if output_folder is None:
        output_folder = last_config_folder
    log.info(f"Following output folder: {output_folder}")

    # // If experiment name not set - search for dervo.yml in parents
    experiment_prefix = args["--experiment_prefix"]
    experiment_name = args.get("--experiment_name")
    if experiment_name is None:
        dervo_yml_path = None
        for path in itertools.chain([last_config_folder], last_config_folder.parents):
            files = [x.name for x in path.iterdir()]
            if "dervo.yml" in files:
                dervo_yml_path = path / "dervo.yml"
                break
        if dervo_yml_path is None:
            raise RuntimeError("Could not find dervo.yml")
        else:
            log.info(f"Found {dervo_yml_path}")
        with dervo_yml_path.open("r") as f:
            cfg = yaml.safe_load(f)
        experiment_name = cfg["run"]
    log.info(f"Experiment_prefix: {experiment_prefix}")
    log.info(f"Experiment_name: {experiment_name}")

    global EXPERIMENT_PATH
    EXPERIMENT_PATH = last_config_folder

    # Setup additional logging
    logfolder = small.mkdir(output_folder / "log")
    id_string = small.get_experiment_id_string()
    small.add_filehandler(logfolder / f"{id_string}.DEBUG.log", logging.DEBUG, "extended")
    small.add_filehandler(logfolder / f"{id_string}.INFO.log", logging.INFO, "short")

    # Load YML configs, merge into a single config
    subconfigs = []
    for config_path in config_paths:
        with Path(config_path).open("r") as f:
            subconfig = yaml.safe_load(f)
        # If we encounter "relative" paths - expand them
        flat_subconfig = flatten_nested_dict(subconfig)
        for k, v in copy.copy(flat_subconfig).items():
            if isinstance(v, str) and v.lower().startswith("py@"):
                flat_subconfig[k] = expand_relative_path(config_path, v)
        subconfig = unflatten_nested_dict(flat_subconfig)
        subconfigs.append(subconfig)
    config = {}
    for subconfig in subconfigs:
        config = gir_merge_dicts(subconfig, config)

    # Retrieve the experiment routine, execute
    experiment_str = f"{experiment_prefix}.{experiment_name}"
    x = experiment_str.split(".")
    module_str = ".".join(x[:-1])
    routine_str = x[-1]

    module = importlib.import_module(module_str)
    routine = getattr(module, routine_str)

    routine(output_folder, config, [])


if __name__ == "__main__":
    log = small.reasonable_logging_setup(logging.INFO)
    dervo_run(docopt(DERVO_DOC))
