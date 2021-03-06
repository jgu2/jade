"""SLURM management functionality"""

import logging
import multiprocessing
import os
import tempfile

from jade.enums import Status
from jade.hpc.common import HpcJobStatus, HpcJobInfo
from jade.hpc.hpc_manager_interface import HpcManagerInterface
from jade.utils.subprocess_manager import SubprocessManager
from jade.utils.utils import create_script


logger = logging.getLogger(__name__)


DEFAULTS = {
    "walltime": 60 * 12,
    "interface": "ib0",
    "local_directory": tempfile.gettempdir(),
    "memory": 5000,
}


class FakeManager(HpcManagerInterface):
    """Simulates management of HPC jobs."""

    _OPTIONAL_CONFIG_PARAMS = {}
    _REQUIRED_CONFIG_PARAMS = ()

    next_job_id = 1

    def __init__(self, _):
        self._subprocess_mgr = None
        self._job_id = None

    def cancel_job(self, job_id):
        return 0

    def check_status(self, name=None, job_id=None):
        if self._subprocess_mgr is None:
            job_info = HpcJobInfo(job_id, "", HpcJobStatus.NONE)
        elif self._subprocess_mgr.in_progress():
            job_info = HpcJobInfo(job_id, "", HpcJobStatus.RUNNING)
        else:
            job_info = HpcJobInfo(job_id, "", HpcJobStatus.COMPLETE)

        logger.debug("status=%s", job_info)
        return job_info

    def check_statuses(self):
        val = {self._job_id: self.check_status(job_id=self._job_id).status}
        return val

    def check_storage_configuration(self):
        pass

    def create_cluster(self):
        pass

    def create_local_cluster(self):
        pass

    def create_submission_script(self, name, script, filename, path):
        lines = [
            "#!/bin/bash",
            script,
        ]
        create_script(filename, "\n".join(lines))

    def get_config(self):
        return {"hpc": {}}

    def get_local_scratch(self):
        for envvar in ("TMP", "TEMP"):
            tmpdir = os.environ.get(envvar)
            if tmpdir:
                return tmpdir
        return "."

    @staticmethod
    def get_num_cpus():
        return multiprocessing.cpu_count()

    def get_optional_config_params(self):
        return self._OPTIONAL_CONFIG_PARAMS

    def get_required_config_params(self):
        return self._REQUIRED_CONFIG_PARAMS

    def log_environment_variables(self):
        pass

    def submit(self, filename):
        self._job_id = str(FakeManager.next_job_id)
        FakeManager.next_job_id += 1
        self._subprocess_mgr = SubprocessManager()
        self._subprocess_mgr.run(filename)
        return Status.GOOD, self._job_id, None
