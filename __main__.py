from src.tools import *
import sys

if __name__ == '__main__':
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
        print("Invalid mode")