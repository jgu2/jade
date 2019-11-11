"""CLI to start a SLURM cluster."""

import logging
import os
import re
import sys

import click

from jade.common import OUTPUT_DIR
from jade.jobs.job_runner import JobRunner
from jade.loggers import setup_logging
from jade.utils.utils import makedirs, get_cli_string


logger = logging.getLogger(__name__)


@click.argument(
    "config-file",
    type=str,
)
@click.option(
    "-o", "--output",
    default=OUTPUT_DIR,
    show_default=True,
    help="Output directory."
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable verbose log output."
)
@click.command()
def run_jobs(config_file, output=OUTPUT_DIR, verbose=False):
    """Starts jobs on HPC."""
    match = re.search(r"batch_(\d+)\.json", config_file)
    assert match
    batch_id = match.group(1)
    makedirs(output)
    filename = os.path.join(output, f"run_jobs_batch_{batch_id}.log")
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, filename, file_level=level, console_level=level)
    logger.info(get_cli_string())

    mgr = JobRunner(config_file, output=output, batch_id=batch_id)
    ret = mgr.run_jobs(verbose=verbose)
    sys.exit(ret.value)