import subprocess
import logging
import sys

LOGGER = logging.getLogger(__name__)

def wait_for_procs(procs: list[subprocess.Popen[str]]):
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt as e:
        LOGGER.warning("Received interrupt signal, exiting")
        raise e

def spawn_cmd(cmd_str: str, always_pipe_output=False):
    LOGGER.info('Executing: %s', cmd_str)
    cmd_args = cmd_str.split()
    try:
        if always_pipe_output or LOGGER.getEffectiveLevel() == logging.DEBUG:
            return subprocess.Popen(cmd_args, text=True)
        return subprocess.Popen(cmd_args, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, text=True)
    except Exception as e:
        LOGGER.exception(e)
        sys.exit(1)

def run_cmd(cmd_str: str, always_pipe_output=False):
    LOGGER.info('Executing: %s', cmd_str,)
    cmd_args = cmd_str.split()
    if always_pipe_output or LOGGER.getEffectiveLevel() == logging.DEBUG:
        return subprocess.run(cmd_args, text=True, check=False)
    return subprocess.run(cmd_args, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)
