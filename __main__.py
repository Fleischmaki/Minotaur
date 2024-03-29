from src.tools import *
import sys, logging
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
        log = logging.INFO
    else:
        log = log[2:]
        if log == 'E':
            log = logging.ERROR
        elif log == 'W':
            log = logging.WARNING
        elif log == 'I':
            log = logging.INFO
        elif log == 'D':
            log = logging.DEBUG
        argv = argv[1:]
    logging.basicConfig(level=log, format='%(levelname)s: %(message)s', style='%')

    if mode == "t":
        test.load(argv)
    elif mode == "m":
        minimize.Minimizer(argv).minimize()
    elif mode == "g":
        generate.load(argv)
    elif mode == "e":
        experiment.load(argv)
    elif mode == "c":
        check_files.load(argv) 
    else:
        LOGGER.error("Invalid mode")