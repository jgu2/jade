"""CLI to automatically create a configuration."""

import logging
import click

from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.exceptions import InvalidExtension
from jade.extensions.registry import Registry, ExtensionClassType
from jade.jobs.job_post_process import JobPostProcess
from jade.utils.utils import load_data


# TODO: need one group command for auto-config; this should be a subcommand.


@click.option(
    "-v", "--verbose",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable verbose log output."
)
@click.option(
    "-c", "--config-file",
    default=CONFIG_FILE,
    show_default=True,
    help="config file to generate."
)
@click.option(
    "-p", "--post-process-config-file",
    is_eager=True,
    help="TOML file post-process config"
)
@click.argument("inputs")
@click.argument("extension")
@click.command()
def auto_config(extension, inputs, config_file, post_process_config_file,
                verbose):
    """Automatically create a configuration."""
    level = logging.DEBUG if verbose else logging.WARNING
    setup_logging("auto_config", None, console_level=level)

    post_process_config = None
    if post_process_config_file is not None:
        module, class_name, data = JobPostProcess.load_config_from_file(post_process_config_file)
        # ensure everything ok
        JobPostProcess(module, class_name, data)

        post_process_config = {
            "module": module,
            "class_name": class_name,
            "data": data
        }

    # User extension
    registry = Registry()
    if not registry.is_registered(extension):
        raise InvalidExtension(f"Extension '{extension}' is not registered.")

    cli = registry.get_extension_class(extension, ExtensionClassType.CLI)
    config = cli.auto_config(inputs, post_process_config=post_process_config)
    print(f"Created configuration with {config.get_num_jobs()} jobs.")
    config.dump(config_file)
    print(f"Dumped configuration to {config_file}.")
