import subprocess, logging

LOGGER = logging.getLogger(__name__)

def wait_for_procs(procs: list[subprocess.Popen[str]]):
    for p in procs:
        p.wait()

def spawn_cmd(cmd_str: str):
    LOGGER.info('Executing: %s', cmd_str)
    cmd_args = cmd_str.split()
    try:
        if logging.root.level != logging.DEBUG:
            return subprocess.Popen(cmd_args)
        return subprocess.Popen(cmd_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    except Exception as e:
        LOGGER.exception(e)
        exit(1)

def run_cmd(cmd_str: str):
    LOGGER.info('Executing: %s', cmd_str)
    cmd_args = cmd_str.split()
    return subprocess.run(cmd_args, capture_output = logging.root.level == logging.DEBUG, check=False)
