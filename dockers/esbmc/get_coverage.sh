#!/bin/bash
# ARG 1: Outdir
# ARG 2: Outfile
mkdir -p "$1"
python3 -m gcovr -r /home/maze/tools/esbmc/build --json "$1/$2".json