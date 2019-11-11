"""Utility functions for the jade package."""

from datetime import datetime
import functools
import gzip
import logging
import json
import os
import re
import shutil
import stat
import sys
import yaml

import toml

from jade.exceptions import InvalidParameter
from jade.utils.timing_utils import timed_debug


MAX_PATH_LENGTH = 255

logger = logging.getLogger(__name__)


def create_chunks(items, size):
    """Returns a generator dividing items into chunks.

    items : list
    batch_size : int

    Returns
    -------
    generator

    """
    for i in range(0, len(items), size):
        yield items[i: i + size]


def create_script(filename, text, executable=True):
    """Creates a script with the given text.

    Parameters
    ----------
    text : str
        body of script
    filename : str
        file to create
    executable : bool
        if True, set as executable

    """
    # Permissions issues occur when trying to overwrite and then make
    # executable another user's file.
    if os.path.exists(filename):
        os.remove(filename)

    with open(filename, "w") as f_out:
        logger.info("Writing %s", filename)
        f_out.write(text)

    if executable:
        curstat = os.stat(filename)
        os.chmod(filename, curstat.st_mode | stat.S_IEXEC)


def make_directory_read_only(directory):
    """Set all files in the directory to be read-only.

    Parameters
    ----------
    directory : str

    """
    for filename in os.listdir(directory):
        make_file_read_only(os.path.join(directory, filename))

    logger.debug("Made all files in %s read-only", directory)


def make_file_read_only(filename):
    """Set the file to be read-only.

    Parameters
    ----------
    filename : str

    """
    os.chmod(filename, 0o444)
    logger.debug("Set %s as read-only", filename)


def _get_module_from_extension(filename, **kwargs):
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".json":
        mod = json
    elif ext == ".toml":
        mod = toml
    elif ext in (".yml", ".yaml"):
        mod = yaml
    elif "mod" in kwargs:
        mod = kwargs["mod"]
    else:
        raise InvalidParameter(f"Unsupported extension {filename}")

    return mod


@timed_debug
def dump_data(data, filename, **kwargs):
    """Dump data to the filename.
    Supports JSON, TOML, YAML, or custom via kwargs.

    Parameters
    ----------
    data : dict
        data to dump
    filename : str
        file to create or overwrite

    """
    mod = _get_module_from_extension(filename, **kwargs)
    with open(filename, "w") as f_out:
        mod.dump(data, f_out, **kwargs)

    logger.debug("Dumped data to %s", filename)


@timed_debug
def load_data(filename, **kwargs):
    """Load data from the file.
    Supports JSON, TOML, YAML, or custom via kwargs.

    Parameters
    ----------
    filename : str

    Returns
    -------
    dict

    """
    # TODO:  YAMLLoadWarning: calling yaml.load() without Loader=... is deprecated,
    #  as the default Loader is unsafe. Please read https://msg.pyyaml.org/load for full details.
    mod = _get_module_from_extension(filename, **kwargs)
    with open(filename) as f_in:
        data = mod.load(f_in)

    logger.debug("Loaded data from %s", filename)
    return data


def aggregate_data_from_files(directory, end_substring, **kwargs):
    """Aggregate objects from files in directory matching end_substring.
    Refer to :func:`~jade.utils.utils.load_data` for supported file formats.

    Parameters
    ----------
    directory : str
    substring : str

    Returns
    -------
    list of dict

    """
    data = []
    for filename in os.listdir(directory):
        if filename.endswith(end_substring):
            path = os.path.join(directory, filename)
            data.append(load_data(path, **kwargs))

    return data


def makedirs(path):
    """Creates a directory tree if it doesn't exist.

    Parameters
    ----------
    path : str

    """
    if not os.path.exists(path):
        logger.debug("Create directory %s", path)
        try:
            os.makedirs(path)
        except FileExistsError:
            # There may be a race between processes.
            pass


def rmtree(path):
    """Deletes the directory tree if it exists.

    Parameters
    ----------
    path : str

    """
    if os.path.exists(path):
        shutil.rmtree(path)

    logger.debug("Deleted %s", path)


def modify_file(filename, line_func, *args, **kwargs):
    """Modifies a file by running a function on each line.

    Parameters
    ----------
    filename : str
    line_func : callable
        Should return the line to write to the modified file.

    """
    tmp = filename + ".tmp"
    assert not os.path.exists(tmp), f"filename={filename} tmp={tmp}"

    with open(filename) as f_in:
        with open(tmp, "w") as f_out:
            for line in f_in:
                line = line_func(line, *args, **kwargs)
                f_out.write(line)

    shutil.move(tmp, filename)


def get_cli_string():
    """Return the command-line arguments issued.

    Returns
    -------
    str

    """
    return os.path.basename(sys.argv[0]) + " " + " ".join(sys.argv[1:])


def handle_key_error(func):
    """Decorator to catch KeyError exceptions that happen because the user
    performs invalid actions."""
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except KeyError as err:
            msg = "invalid parameter: {}".format(err)
            logger.debug(msg, exc_info=True)
            raise InvalidParameter(msg)

        return result

    return wrapped


def decompress_file(filename):
    """Decompress a file.

    Parameters
    ----------
    filename : str

    Returns
    -------
    str
        Returns the new filename.

    """
    assert os.path.splitext(filename)[1] == ".gz"

    new_filename = filename[:-3]
    with open(new_filename, "wb") as f_out:
        with gzip.open(filename, "rb") as f_in:
            shutil.copyfileobj(f_in, f_out)

    os.remove(filename)
    logger.debug("Decompressed %s", new_filename)
    return new_filename


def get_filenames_by_ext(directory, ext):
    """Return filenames in directory, recursively, with file extension.

    Parameters
    ----------
    directory : str
    ext : str
        file extension, ex: .log

    Returns
    -------
    generator

    """
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if ext in filename:
                yield os.path.join(dirpath, filename)


def interpret_datetime(timestamp):
    """Return a datetime object from a timestamp string.

    Parameters
    ----------
    timestamp : str

    Returns
    -------
    datetime.datetime

    """
    formats = (
        "%Y-%m-%d_%H:%M:%S.%f",
        "%Y-%m-%d_%H-%M-%S-%f",
    )

    for i, fmt in enumerate(formats):
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            if i == len(formats) - 1:
                raise
            continue


def rotate_filenames(directory, ext):
    """Rotates filenames in directory, recursively, to .1, .2, .etc.

    Parameters
    ----------
    directory : str
    ext : str
        file extension, ex: .log

    """
    regex_has_num = re.compile(r"(\d+)(?:\.[a-zA-Z]+)?$")

    for dirpath, _, filenames in os.walk(directory):
        files = []
        for filename in filter(lambda x: ext in x, filenames):
            new_names = set()
            match = regex_has_num.search(filename)
            if match:
                cur = int(match.group(1))
                new = cur + 1
                new_name = filename.replace(f"{ext}.{cur}", f"{ext}.{new}")
            else:
                cur = 0
                if not filename.endswith(ext):
                    # such as compressed files
                    split_ext = os.path.splitext(filename)
                    new_name = split_ext[0] + ".1" + split_ext[1]
                else:
                    new_name = filename + ".1"
            assert new_name not in new_names
            new_names.add(new_name)
            files.append((filename, cur, new_name))

        files.sort(key=lambda x: x[1], reverse=True)
        for filename in files:
            old = os.path.join(dirpath, filename[0])
            new = os.path.join(dirpath, filename[2])
            os.rename(old, new)
            logger.info("Renamed %s to %s", old, new)


def check_filename(name):
    """
    Validates that a name is valid for use as a filename or directory.
    Valid characters:  letters, numbers, underscore, hyphen, period

    Parameters
    ----------
    string: str,
        A given string.

    Raises
    ------
    InvalidParameter
        Raised if the name contains illegal characters or is too long.

    """
    if not re.search(r"^[\w\.-]+$", name):
        raise InvalidParameter(f"{name} contains illegal characters.")

    if len(name) > MAX_PATH_LENGTH:
        raise InvalidParameter(
            f"length of {name} is greater than the limit of {MAX_PATH_LENGTH}."
        )