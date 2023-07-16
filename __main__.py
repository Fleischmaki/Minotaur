import sys, os
import subprocess
from mc2.tools import minimize, test_mc
from mc2.runner import maze_gen

if __name__ == '__main__':
    mode = sys.argv[1]
    if not mode.startswith("-"):
        mode = input("Run tests [r], generate [g] or minimize [m]")
        argv = sys.argv[1:]
    else:
        mode = mode[1:]
        argv = sys.argv[2:]

    if mode == "r":
        test_mc.load(argv)
    elif mode == "m":
        minimize.load(argv)
    elif mode == "g":
        print("Not Implemented")
    else:
        print("Invalid mode")