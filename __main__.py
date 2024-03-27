from src.tools import *
import sys, logging
LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    mode = sys.argv[1]
    if not mode.startswith("--"):
        mode = input("Run tests [t], experiment [e], generate maze [g] or minimize [m]")
        argv = sys.argv[1:]
    else:
        mode = mode[2:]
        argv = sys.argv[2:]

    if mode == "t":
        test.load(argv)
    elif mode == "m":
        minimize.Minimizer(argv).minimize()
    elif mode == "g":
        generate.load(argv)
    elif mode == "e":
        experiment.load(argv)
    else:
        LOGGER.error("Invalid mode")