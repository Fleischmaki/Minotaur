""" Main entry point, switch functionality and set log_level
"""
import sys
import logging
from src.tools import test, experiment, generate
pysmt = 'pysmt' in sys.modules
if pysmt:
    from src.tools import minimize, check_files
LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    mode = sys.argv[1]
    if not mode.startswith("--"):
        mode = input("Run tests [t], experiment [e], generate maze [g] or minimize [m]")
        argv = sys.argv[1:]
    else:
        mode = mode[2:]
        argv = sys.argv[2:]
    log = argv[0]
    if not log.startswith("--"):
        LOG = logging.INFO
    else:
        LOG = log[2:]
        if LOG == 'E':
            LOG = logging.ERROR
        elif LOG == 'W':
            LOG = logging.WARNING
        elif LOG == 'I':
            LOG = logging.INFO
        elif LOG == 'D':
            LOG = logging.DEBUG
        argv = argv[1:]
    logging.basicConfig(level=LOG, format='%(levelname)s: %(message)s', style='%')

    if mode == "t":
        test.load(argv)
    elif mode == "m" and pysmt:
        minimize.Minimizer(argv).minimize()
    elif mode == "g":
        generate.load(argv)
    elif mode == "e":
        experiment.load(argv)
    elif mode == "c" and pysmt:
        check_files.load(argv)
    else:
        LOGGER.error("Invalid mode" + ("" if pysmt else "Have you tried installing pysmt?"))
