import subprocess, logging

LOGGER = logging.getLogger(__name__)

def wait_for_procs(procs: 'list[subprocess.Popen[str]]'):
    for p in procs:
        p.wait()

def spawn_cmd(cmd_str: str):
    LOGGER.info('Executing: %s' % cmd_str)
    cmd_args = cmd_str.split()
    try:
        return subprocess.Popen(cmd_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    except Exception as e:
        print(e)
        exit(1)

def run_cmd(cmd_str: str):
    LOGGER.info('Executing: %s' % cmd_str)
    cmd_args = cmd_str.split()
    return subprocess.run(cmd_args)
