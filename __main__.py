import sys, os
import subprocess
from mc2.tools import minimize, test_mc
from mc2.runner import maze_gen

if __name__ == '__main__':
    mode = sys.argv[1]
    if not mode.startswith("--"):
        mode = input("Run tests [t], generate maze [g] or minimize [m]")
        argv = sys.argv[1:]
    else:
        mode = mode[2:]
        argv = sys.argv[2:]

    if mode == "t":
        test_mc.load(argv)
    elif mode == "m":
        minimize.load(argv)
    elif mode == "g":
        maze_gen.load(argv)
    else:
        print("Invalid mode")